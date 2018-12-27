%import common.WS
%import common.LCASE_LETTER
%import common.LETTER
%import common.DIGIT
%import common.ESCAPED_STRING

query: WSCOMM? ((command | queryoption | editopers | oper) WSCOMM?)+

command: "|" WS? stormcmd WSCOMM? ["|"]

queryoption: "%" WS? OPTSETS WS? "=" ALPHANUMS
editopers: "[" WS? (editoper WS?)* "]"
editoper: editnodeadd | edittagadd // et al
editnodeadd: ABSPROP WS? "=" WS? valu
edittagadd: "+" tagname [WS? "=" valu]
ABSPROP: VARSETS // must be a propname

oper: formpivot | formpivotin | opervarlist | filtoper | liftbytag | liftpropby | liftprop | stormcmd | operrelprop
    | forloop | switchcase | "break" | "continue" | valuvar

forloop: "for" WS? (VARNAME | varlist) WS? "in" WS? VARNAME WS? subquery
subquery: "{" query? "}"
switchcase: "switch" WS? varvalu WS? "{" (WSCOMM? (("*" WS? ":" subquery) | (CASEVALU WSCOMM? subquery)) )* WSCOMM? "}"
varlist: "(" [WS? VARNAME (WS? "," WS? VARNAME)*] WS? ["," WS?] ")"
CASEVALU: (DOUBLEQUOTEDSTRING WSCOMM? ":") | /[^:]+:/

OPTSETS: LCASE_LETTER+
ALPHANUMS: (LETTER | DIGIT)+
VARSETS: ("$" | "." | ":" | LETTER | DIGIT)+

formpivot: "->" WS? ("*" | TAGMATCH | ABSPROP)
formpivotin: "<-" WS? ("*" | ABSPROP)
opervarlist: varlist WS? "=" WS? valu

operrelprop: RELPROP [WS? (proppivot | propjoin)]
proppivot: "->" WS? ("*" | ABSPROP)
propjoin: "-*>" WS? ABSPROP

valuvar: VARNAME WS? "=" WS? valu

liftpropby: PROPNAME WS? CMPR WS? valu
liftprop: PROPNAME
liftbytag: tagname
tagname: "#" WS? (VARNAME | TAG)

VARNAME: "$" WS? VARTOKN
VARTOKN: VARCHARS
VARCHARS: (LETTER | DIGIT | "_")+
stormcmd: CMDNAME (WS cmdargv)* [WS? "|"]
cmdargv: subquery | DOUBLEQUOTEDSTRING | SINGLEQUOTEDSTRING | NONCMDQUOTE
TAG: /[^=\)\]},@ \t\n]/+
TAGMATCH: /#[^=)\]},@ \t\n]*/

CMPR: /\*.*?=|[!<>@^~=]+/
valu: NONQUOTEWORD | valulist | DOUBLEQUOTEDSTRING | SINGLEQUOTEDSTRING | varvalu | tagname | RELPROPVALU
    | UNIVPROPVALU // and more
valulist: "(" [WS? valu (WS? "," WS? valu)*] WS? ["," WS?] ")"

NONCMDQUOTE: /[^ \t\n|}]+/
NONQUOTEWORD: (LETTER | DIGIT | "-" | "?") /[^ \t\n\),=\]}|]*/

varvalu:  VARNAME (VARDEREF | varcall)* // et al
varcall: valulist
filtoper: ("+" | "-") cond

cond: condexpr | (WSCOMM? condsubq) | ((RELPROP | tagname | UNIVPROP | ABSPROP) [WS? CMPR WS? valu]) // et al
condexpr: "(" WS? cond (WS? (("and" | "or") WS? cond))* WS? ")"
condsubq: "{" WSCOMM? query WS? "}" [WSCOMM? CMPR valu]
VARDEREF: "." VARTOKN
DOUBLEQUOTEDSTRING: ESCAPED_STRING
SINGLEQUOTEDSTRING: "'" /[^']/ "'"
UNIVPROP:  "." VARSETS
UNIVPROPVALU: UNIVPROP

RELPROP: ":" VARSETS
RELPROPVALU: RELPROP

// Whitespace or comments
WSCOMM: (CCOMMENT | CPPCOMMENT | WS)+

// From https://stackoverflow.com/a/36328890/6518334
CCOMMENT: /\/\*+[^*]*\*+(?:[^\/*][^*]*\*+)*\//
CPPCOMMENT: /\/\/[^\n]*/

// TOOD:  fix all one-word propnames and define propname as word with a colon
PROPNAME: "inet:fqdn" | "inet:dns:a" | "inet:dns:query" | "syn:tag" | "teststr:tick" | "teststr" | ".created"
    | "refs" | ".seen" | "testcomp:haha" | "testcomp" | "testint:loc" | "testint"
    | ".favcolor" | "file:bytes:size" | "pivcomp" | "pivtarg" | "inet:ipv4" | "seen:source" | "inet:user"
    | "ps:person" | "geo:place:latlong" | "geo:place" | "cluster" | "testguid" | "inet:asn"
    | "tel:mob:telem:latlong" // FIXME: all the props

CMDNAME: "help" | "iden" | "movetag" | "noderefs" | "sudo" | "limit" | "reindex" | "delnode" | "uniq" | "count"
    | "spin" | "graph" // FIXME: all the commands
