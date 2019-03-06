%import common.WS -> _WS
%import common.LCASE_LETTER
%import common.LETTER
%import common.DIGIT
%import common.ESCAPED_STRING

query: _WSCOMM? ((command | queryoption | _editopers | _oper) _WSCOMM?)*

command: "|" _WS? stormcmd _WSCOMM? ["|"]

queryoption: "%" _WS? LCASE_LETTER+ _WS? "=" (LETTER | DIGIT)+
_editopers: "[" _WS? (_editoper _WS?)* "]"
_editoper: editpropset | editunivset | edittagadd | editpropdel | editunivdel | edittagdel | editnodeadd
edittagadd: "+" tagname [_WS? "=" _valu]
editunivdel: "-" UNIVPROP
edittagdel: "-" tagname
editpropset: RELPROP _WS? "=" _WS? _valu
editpropdel: "-" RELPROP
editunivset: UNIVPROP _WS? "=" _WS? _valu
editnodeadd: ABSPROP _WS? "=" _WS? _valu
ABSPROP: VARSETS // must be a propname

_oper: subquery | formpivot | formjoin | formpivotin | formjoinin | lifttagtag | opervarlist | filtoper | liftbytag
    | _liftprop | stormcmd | operrelprop | forloop | switchcase | "break" | "continue" | valuvar

forloop: "for" _WS? (_varname | varlist) _WS? "in" _WS? varvalu _WS? subquery
subquery: "{" query "}"
switchcase: "switch" _WS? varvalu _WS? "{" (_WSCOMM? (("*" _WS? ":" subquery) | (CASEVALU _WSCOMM? subquery)) )* _WSCOMM? "}"
varlist: "(" [_WS? _varname (_WS? "," _WS? _varname)*] _WS? ["," _WS?] ")"
CASEVALU: (DOUBLEQUOTEDSTRING _WSCOMM? ":") | /[^:]+:/

// Note: changed from syntax.py in that cannot start with ':' or '.'
VARSETS: ("$" | "." | LETTER | DIGIT) ("$" | "." | ":" | LETTER | DIGIT)*

// TODO: TAGMATCH and tagname/TAG are redundant
formpivot: "->" _WS? ("*" | TAGMATCH | ABSPROP)
formjoin:   "-+>" _WS? ("*" | ABSPROP)
formpivotin: "<-" _WS? ("*" | ABSPROP)
formjoinin: "<+-" _WS? ("*" | ABSPROP)
opervarlist: varlist _WS? "=" _WS? _valu

operrelprop: RELPROP [_WS? (_proppivot | propjoin)]
_proppivot: "->" _WS? ("*" | ABSPROP)
propjoin: "-*>" _WS? ABSPROP

valuvar: _varname _WS? "=" _WS? _valu

_liftprop: liftpropby | liftprop
liftprop: PROPNAME
liftpropby: PROPNAME ((tagname [_WS? CMPR _valu]) | (_WS? CMPR _WS? _valu))
lifttagtag: "#" tagname
liftbytag: tagname
tagname: "#" _WS? (_varname | TAG)

_varname: "$" _WS? VARTOKN
VARTOKN: VARCHARS
VARCHARS: (LETTER | DIGIT | "_")+
stormcmd: CMDNAME (_WS cmdargv)* [_WS? "|"]
cmdargv: subquery | DOUBLEQUOTEDSTRING | SINGLEQUOTEDSTRING | NONCMDQUOTE

// Note: different from syntax.py in explicitly disallowing # as first char
// FIXME: encode tag re directly: ^([\w]+\.)*[\w]+ (currently in semantic?!
TAG: /[^#=)\]},@ \t\n][^=)\]},@ \t\n]*/
TAGMATCH: /#[^=)\]},@ \t\n]*/

CMPR: /\*[^=]*=|[!<>@^~=]+/
_valu: NONQUOTEWORD | valulist | varvalu | RELPROPVALU | UNIVPROPVALU | tagname | DOUBLEQUOTEDSTRING
    | SINGLEQUOTEDSTRING
valulist: "(" [_WS? _valu (_WS? "," _WS? _valu)*] _WS? ["," _WS?] ")"

NONCMDQUOTE: /[^ \t\n|}]+/
NONQUOTEWORD: (LETTER | DIGIT | "-" | "?") /[^ \t\n),=\]}|]*/

varvalu:  _varname (VARDEREF | varcall)*
varcall: valulist
filtoper: ("+" | "-") cond

cond: condexpr | condsubq | ("not" _WS? cond)
    | ((RELPROP | UNIVPROP | tagname | ABSPROP) [_WS? CMPR _WS? _valu])
condexpr: "(" _WS? cond (_WS? (("and" | "or") _WS? cond))* _WS? ")"
condsubq: "{" _WSCOMM? query _WS? "}" [_WSCOMM? CMPR _valu]
VARDEREF: "." VARTOKN
DOUBLEQUOTEDSTRING: ESCAPED_STRING
SINGLEQUOTEDSTRING: "'" /[^']/ "'"
UNIVPROP:  "." VARSETS
UNIVPROPVALU: UNIVPROP

RELPROP: ":" VARSETS
RELPROPVALU: RELPROP

// Whitespace or comments
_WSCOMM: (CCOMMENT | CPPCOMMENT | _WS)+

// From https://stackoverflow.com/a/36328890/6518334
CCOMMENT: /\/\*+[^*]*\*+([^\/*][^*]*\*+)*\//
CPPCOMMENT: /\/\/[^\n]*/

// TOOD:  fix all one-word propnames and define propname as word with a colon
PROPNAME: "inet:fqdn" | "inet:dns:a" | "inet:dns:query" | "syn:tag" | "teststr:tick" | "teststr" | ".created"
    | "refs" | ".seen" | "testcomp:haha" | "testcomp" | "testint:loc" | "testint" | "wentto"
    | "file:bytes:size" | "pivcomp:tick" | "pivcomp" | "pivtarg" | "inet:ipv4:loc"
    | "inet:ipv4" | "seen:source" | "inet:user" | "media:news"
    | "ps:person" | "geo:place:latlong" | "geo:place" | "cluster" | "testguid" | "inet:asn"
    | "tel:mob:telem:latlong" | "source" // FIXME: all the props

CMDNAME: "help" | "iden" | "movetag" | "noderefs" | "sudo" | "limit" | "reindex" | "delnode" | "uniq" | "count"
    | "spin" | "graph" | "max" | "min" | "sleep" // FIXME: all the commands
