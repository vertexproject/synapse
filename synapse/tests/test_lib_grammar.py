import lark  # type: ignore

import synapse.exc as s_exc

import synapse.lib.parser as s_parser
import synapse.lib.datfile as s_datfile
import synapse.lib.grammar as s_grammar

import synapse.tests.utils as s_t_utils

# flake8: noqa: E501

Queries = [
    '$foo=(-$foo)',
    '$foo=(-#foo)',
    '$foo=(-.foo)',
    '$foo=(-:foo)',
    '$foo=(-($foo-1))',
    '$foo=(--$foo)',
    '$foo=(5---$foo)',
    '$foo=(5+-$foo)',
    '$foo=(5+--$foo)',
    '$foo=(#$tag:$tagprop)',
    '#$tag:$tagprop',
    '#$tag:$tagprop=$valu',
    '[+#$tag:$tagprop=$valu]',
    '$lib.print(`ip={$node.repr()} asn={:asn} .seen={.seen} foo={#foo} {:asn=5}`)',
    'inet:ipv4=45.79.131.138 -> inet:flow -(:dst:port=444 or :dst:port=80)',
    'media:news=0c7f7267d3b62432cb0d7d0e9d3108a4 -(refs)> inet:ipv4',
    '$foo=(2) return(($foo+(1)))',
    '$foo=(2) return(($foo-(1)))',
    'return(((2)+(1)))',
    'return(((2)-(1)))',
    '$foo=(2) return(($foo<(3)))',
    'return(((2)<(3)))',
    'return(((1)<(3)-(1)))',
    'return(((1)<(3)-(1)))',
    '$foo=(2) return(($foo<(4)-(1)))',
    '[inet:ipv4=1.2.3.4 :asn=1] return((:asn<(4)-(1)))',
    '$p=asn inet:ipv4=1.2.3.4 return((:$p<(4)-(1)))',
    '[inet:ipv4=1.2.3.4 .test:univ=0] return((.test:univ<(4)-(1)))',
    '[inet:ipv4=1.2.3.4 +#foo:score=1] return((#foo:score<(4)-(1)))',
    '[inet:ipv4=1.2.3.4 +#foo=(0)] return((#foo<(4)-(1)))',
    '$p=bar [inet:ipv4=1.2.3.4 +#foo.bar=(0)] return((#foo.$p<(4)-(1)))',
    '[inet:asn=1 inet:asn=2 <("foo)")+ { inet:ipv4=1.2.3.4 }]',
    'inet:asn <(2)',
    'inet:asn <("foo)")- *',
    'inet:asn <(("foo)", \'bar()\'))- *',
    'emit $foo stop',
    'try { inet:ipv4=asdf } catch TypeError as err { }',
    'try { inet:ipv4=asdf } catch FooBar as err { } catch * as err { }',
    'test:array*[=1.2.3.4]',
    'macro.set hehe ${ inet:ipv4 }',
    '$q=${#foo.bar}',
    'metrics.edits.byprop inet:fqdn:domain --newv $lib.null',
    'tee // comment',
    'inet:fqdn=newp.com\n | tee\n { inet:fqdn } // faz\n | uniq',
    'inet:fqdn=newp.com\n | tee\n { inet:fqdn }\n /* faz */\n | uniq',
    'hehe.haha\xa0foo // a comment | uniq ',
    'inet:ipv4 --> *',
    'inet:ipv4 <-- *',
    'inet:fqdn=woot.com\xa0[ <(refs)+ { media:news } ]',
    'inet:fqdn=woot.com [ <(refs)+ { media:news } ]',
    '$refs = refs media:news -($refs)> * -(#foo or #bar)',
    '$refs = refs media:news <($refs)- (inet:ipv4,inet:ipv6) -(#foo or #bar)',
    'media:news -(refs)> * -(#foo or #bar)',
    'media:news <(refs)- $bar -(#foo or #bar)',
    'media:news [ -(refs)> { inet:fqdn=woot.com } ]',
    'media:news [ +(refs)> { inet:fqdn=woot.com } ]',
    'cron add --monthly=-1:12:30 {#bar}',
    '$foo=$(1 or 1 or 0)',
    '$foo=$(1 and 1 and 0)',
    '$var=tag1 #base.$var',
    'test:str $var=tag1 +#base.$var@=2014',
    'test:str $var=tag1 -> #base.$var',
    '$var=hehe [test:str=foo :$var=heval]',
    '[test:str=heval] test:str $var=hehe +:$var',
    '[test:str=foo :tick=2019] $var=tick [-:$var]',
    'test:str=foo $var=hehe :$var -> test:str',
    'test:str=foo $var=seen [.$var=2019]',
    'test:str $var="seen" +.$var',
    'test:str=foo $var="seen" [ -.$var ] | spin | test:str=foo',
    '$var=hehe [test:str=foo :$hehe=heval]',
    '#tag.$bar',
    '+#tag.$bar',
    '+#tag.$bar.*',
    '''#tag.$"escaped \\"string\\""''',
    '''+#tag.$"escaped \\"string\\"".*''',
    '''[+#tag.$"escaped \\"string\\""]''',
    r'''test:str $"some\bvar"=$node.repr()''',
    '$x = 0 while $($x < 10) { $x=$($x+1) [test:int=$x] }',
    '[test:int?=4] [ test:int?=nonono ]',
    '[test:int=4\xa0+?#hehe.haha +?#hehe.newp=newp +#hehe.yes=2020]',
    '[test:str=foo :tick?=2019 ]',
    '[test:str=a] switch $node.form() { hehe\xa0: {[+#baz]} }',
    '[test:type10=2 :strprop=1] spin | test:type10 +$(:strprop) $foo=1 +$foo',
    'inet:fqdn#xxx.xxxxxx.xxxx.xx for $tag in $node.tags(xxx.xxxxxx.*.xx) { <- inet:dns:a +#xx <- meta:note [ +#foo]  ->inet:dns:a }',
    ' +(syn:tag~=aka.*.mal.*)',
    '+(syn:tag^=aka or syn:tag^=cno or syn:tag^=rep)',
    '[test:str=foo][test:int=42]',
    '|help',
    "[ test:str=abcd :tick=2015 +#cool ]",
    '{ #baz } test:str=foo',
    '##baz.faz',
    '#$tag [ -#$tag ]',
    '#$tag',
    '#foo',
    ' #foo',
    '#foo ',
    '#hehe.haha',
    '$hehe.haha',
    '#test.bar +test:pivcomp -+> *',
    '#test.bar +test:pivcomp -> *',
    '#test.bar +test:str <+- *',
    '#test.bar +test:str <- *',
    'test:migr <- meta:note',
    '#test.bar -#test -+> *',
    '#test.bar -#test -> *',
    '#test.bar -#test <+- *',
    '#test.bar -#test <- *',
    '$bar=5.5.5.5 [ inet:ipv4=$bar ]',
    '$blah = ({"foo": "vertex.link"}) [ inet:fqdn=$blah.foo ]',
    '($tick, $tock) = .seen',
    '.created',
    '.created<2010',
    '.created>2010',
    '.created*range=("2010", "?")',
    '.created*range=(2010, 3001)',
    '.created="2001"',
    '.created="{created}"',
    '.seen [ -.seen ]',
    '.seen~="^r"',
    "[meta:note='*' :type=m1]",
    '[ geo:place="*" :latlong=(-30.0,20.22) ]',
    '[ inet:asn=200 :name=visi ]',
    '[ inet:dns:a = ( woot.com , 12.34.56.78 ) ]',
    '[ inet:dns:a=$blob.split("|") ]',
    '[ inet:dns:a=(vertex.link, 5.5.5.5) +#nope ]',
    '[ inet:dns:a=(woot.com,1.2.3.4) ]',
    '[ inet:dns:a=(woot.com, 1.2.3.4) +#yepr ]',
    '[ inet:dns:a=(woot.com, 1.2.3.4) inet:dns:a=(vertex.link, 1.2.3.4) ]',
    '[ inet:dns:a=(woot.com,1.2.3.4) .seen=(2015,2016) ]',
    '[ inet:fqdn = hehe.com inet:ipv4 = 127.0.0.1 hash:md5 = d41d8cd98f00b204e9800998ecf8427e]',
    '[ inet:fqdn = woot.com ]',
    '[ inet:fqdn=vertex.link inet:ipv4=1.2.3.4 ]',
    '[ inet:fqdn=woot.com +#bad=(2015,2016) ]',
    '[ inet:fqdn=woot.com ] -> *',
    '[ inet:fqdn=woot.com inet:fqdn=vertex.link ] [ inet:user = :zone ] +inet:user',
    '[ inet:ipv4 = 94.75.194.194 :loc = nl ]',
    '[ inet:ipv4=$foo ]',
    '[ test:int=$hehe.haha ]',
    '[ inet:ipv4=1.2.3.0/30 inet:ipv4=5.5.5.5 ]',
    '[ inet:ipv4=1.2.3.4 :asn=2 ]',
    '[ inet:ipv4=1.2.3.4 :loc=us inet:dns:a=(vertex.link,1.2.3.4) ]',
    '[ inet:ipv4=1.2.3.4 ]',
    '[ inet:ipv4=192.168.1.0/24]',
    '[ inet:ipv4=4.3.2.1 :loc=zz inet:dns:a=(example.com,4.3.2.1) ]',
    '[inet:ipv4=197.231.221.211 :asn=37560 :loc=lr.lo.voinjama :latlong="8.4219,-9.7478" :dns:rev=exit1.ipredator.se +#cno.anon.tor.exit = (2017/12/19, 2019/02/15) ]',
    '[ inet:user=visi inet:user=whippit ]',
    '[ test:comp=(10, haha) +#foo.bar -#foo.bar ]',
    '[ test:comp=(127,newp) ] [test:comp=(127,127)]',
    "[test:comp=(123, test) test:comp=(123, duck) test:comp=(123, mode)]",
    '[ test:guid="*" :tick=2015 ]',
    '[ test:guid="*" :tick=2016 ]',
    '[ test:guid="*" :tick=2017 ]',
    '[ test:pivcomp=(foo,bar) :tick=2018 ]',
    '[ test:pivcomp=(foo,bar) ]',
    '[ test:pivcomp=(hehe,haha) :tick=2015 +#foo=(2014,2016) ]',
    '[ test:pivcomp=(xxx,yyy) :width=42 ]',
    '[ test:str="foo bar" :tick=2018]',
    '[ test:str=bar +#baz ]',
    '[ test:str=foo +#$tag ]',
    'test:str=foo +#$tag',
    '[ test:str=foo +#bar ] +(#baz or not .seen)',
    '[ test:str=foo +#bar ] +(not .seen)',
    '[ test:str=foo +#bar ] { [ +#baz ] -#bar }',
    '[ test:str=foo test:str=bar ] | sleep 10',
    '[ test:str=foo test:str=bar ] | spin',
    '[ test:str=foo test:str=bar ]',
    '[ test:str=foo test:str=bar test:int=42 ]',
    '[ test:str=haha +#bar=2015 ]',
    '[ test:str=haha +#foo ]',
    '[ test:str=hehe +#foo=(2014,2016) ]',
    '[ test:str=hehe ]',
    '[ test:str=oof +#bar ] { [ test:int=0xdeadbeef ] }',
    '[ test:str=visi +#foo.bar ] -> # [ +#baz.faz ]',
    '[ test:str=visi +#foo.bar ] -> #',
    '[ test:str=visi test:int=20 +#foo.bar ]',
    '[ test:str=woot +#foo=(2015,2018) +#bar .seen=(2014,2016) ]',
    '[ test:str=woot +#foo=(2015,2018) .seen=(2014,2016) ]',
    '[ test:str=woot +#foo=(2015,2018) ]',
    '[ test:str=woot .seen=(2014,2015) ]',
    '[ test:str=woot .seen=20 ]',
    '[-#foo]',
    '[meta:source=((test:str, foobar), (test:str, foo))]',
    '[meta:source=((test:comp, (2048, horton)), (test:comp, (4096, whoville)))]',
    '[meta:source=((test:comp, (9001, "A mean one")), (test:comp, (40000, greeneggs)))]',
    '[meta:source=((test:int, 16), (test:comp, (9999, greenham)))]',
    '[meta:source=((test:str, 123), (test:int, 123))]',
    '[inet:dns:query=(tcp://1.2.3.4, "", 1)]',
    '[inet:dns:query=(tcp://1.2.3.4, "foo*.haha.com", 1)]',
    '[inet:ipv4=1.2.3.1-1.2.3.3]',
    '[inet:ipv4=1.2.3.4 :asn=10] [meta:source=(abcd, (inet:asn, 10))]',
    '[meta:source=(abcd, (test:str, pennywise))]',
    '[meta:source=abcd +#omit.nopiv] [meta:source=(abcd, (test:pivtarg, foo))]',
    '[test:comp=(1234, 5678)]',
    '[test:comp=(3, foob) +#meep.gorp +#bleep.zlorp +#cond]',
    '[test:guid="*" :tick=2001]',
    '[test:guid=abcd :tick=2015]',
    '[test:int=1 test:int=2 test:int=3]',
    '[test:int=10 :loc=us.va]',
    '[test:int=2 :loc=us.va.sydney]',
    '[test:int=20]',
    '[test:int=3 :loc=""]',
    '[test:int=4 :loc=us.va.fairfax]',
    '[test:int=9 :loc=us.ओं]',
    '[test:int=99999]',
    '[test:pivcomp=(foo, 123)]',
    '[test:str=beep test:str=boop]',
    '[test:str=foo :tick=201808021201]',
    '[test:str=hehe] | iden abcd | count',
    '[test:str=hello]',
    'meta:source +:node*range=((test:comp, (1000, green)), (test:comp, (3000, ham)))',
    'meta:source',
    'file:bytes:size=4',
    'for $fqdn in $fqdns { [ inet:fqdn=$fqdn ] }',
    'for ($fqdn, $ipv4) in $dnsa { [ inet:dns:a=($fqdn,$ipv4) ] }',
    'for ($fqdn,$ipv4,$boom) in $dnsa { [ inet:dns:a=($fqdn,$ipv4) ] }',
    'geo:place +geo:place:latlong*near=((34.1, -118.3), 10km)',
    'geo:place -:latlong*near=((34.1, -118.3), 50m)',
    'geo:place:latlong*near=(("34.118560", "-118.300370"), 2600m)',
    'geo:place:latlong*near=(("34.118560", "-118.300370"), 50m)',
    'geo:place:latlong*near=((0, 0), 50m)',
    'geo:place:latlong*near=((34.1, -118.3), 10km)',
    'geo:place=$place <- meta:source <- *',
    'geo:place=$place <- meta:source <- ps:person',
    'geo:place=abcd $latlong=:latlong $radius=:radius | spin | tel:mob:telem:latlong*near=($latlong, 3km)',
    'meta:note=abcd | noderefs -d 2 --join',
    'help',
    'iden 2cdd997872b10a65407ad5fadfa28e0d',
    'iden deadb33f',
    '$foo=42 iden deadb33f',
    'inet:asn=10 | noderefs -of inet:ipv4 --join -d 3',
    'inet:dns:a +{ :ipv4 -> inet:ipv4 +:loc=us }',
    'inet:dns:a +{ :ipv4 -> inet:ipv4 -:loc=us }',
    'inet:dns:a -{ :ipv4 -> inet:ipv4 +:loc=us }',
    'inet:dns:a -{ :ipv4 -> inet:ipv4 -:loc=us }',
    'inet:dns:a :ipv4 -> *',
    'inet:dns:a = (woot.com,  12.34.56.78) [ .seen=( 201708010123, 201708100456 ) ]',
    'inet:dns:a = (woot.com,  12.34.56.78) [ .seen=( 201708010123, \"?\" ) ]',
    'inet:dns:a',
    'inet:dns:a=(woot.com,1.2.3.4) $hehe=:fqdn +:fqdn=$hehe',
    'inet:dns:a=(woot.com,1.2.3.4) $hehe=:fqdn -:fqdn=$hehe',
    'inet:dns:a=(woot.com,1.2.3.4) $hehe=:fqdn inet:fqdn=$hehe',
    'inet:dns:a=(woot.com,1.2.3.4) $newp=.seen',
    'inet:dns:a=(woot.com,1.2.3.4) $seen=.seen :fqdn -> inet:fqdn [ .seen=$seen ]',
    'inet:dns:a=(woot.com,1.2.3.4) [ .seen=(2015,2018) ]',
    'inet:dns:query=(tcp://1.2.3.4, "", 1) :name -> inet:fqdn',
    'inet:dns:query=(tcp://1.2.3.4, "foo*.haha.com", 1) :name -> inet:fqdn',
    'inet:fqdn +#bad $fqdnbad=#bad -> inet:dns:a:fqdn +.seen@=$fqdnbad',
    'inet:fqdn=woot.com -> inet:dns:a -> inet:ipv4',
    'inet:fqdn=woot.com -> inet:dns:a',
    'inet:fqdn=woot.com | delnode',
    'inet:fqdn | graph --filter { -#nope }',
    'inet:fqdn=woot.com',
    'inet:ipv4 +:asn::name=visi',
    'inet:ipv4 +inet:ipv4=1.2.3.0/30',
    'inet:ipv4 +inet:ipv4=1.2.3.1-1.2.3.3',
    'inet:ipv4 +inet:ipv4=10.2.1.4/32',
    'inet:ipv4 -> test:str',
    'inet:ipv4 | reindex --subs',
    'inet:ipv4:loc=us',
    'inet:ipv4:loc=zz',
    'inet:ipv4=1.2.3.1-1.2.3.3',
    'inet:ipv4=192.168.1.0/24',
    'inet:ipv4=1.2.3.4 +:asn',
    'inet:ipv4=1.2.3.4 +{ -> inet:dns:a } < 2 ',
    'inet:ipv4=1.2.3.4 +( { -> inet:dns:a }<=1 )',
    'inet:ipv4=1.2.3.4 +( { -> inet:dns:a } !=2 )',
    'inet:ipv4=1.2.3.4|limit 20',
    'inet:ipv4=12.34.56.78 [ :loc = us.oh.wilmington ]',
    'inet:ipv4=12.34.56.78 inet:fqdn=woot.com [ inet:ipv4=1.2.3.4 :asn=10101 inet:fqdn=woowoo.com +#my.tag ]',
    'inet:user | limit --woot',
    'inet:user | limit 1',
    'inet:user | limit 10 | +inet:user=visi',
    'inet:user | limit 10 | [ +#foo.bar ]',
    'media:news = 00a1f0d928e25729b9e86e2d08c127ce [ :summary = \"\" ]',
    'meta:source:meta:source=$sorc -> *',
    'meta:source:meta:source=$sorc :node -> *',
    'meta:source=8f1401de15918358d5247e21ca29a814',
    'movetag a.b a.m',
    'movetag hehe woot',
    'ps:person=$pers -> meta:source -> *',
    'ps:person=$pers -> meta:source -> geo:place',
    'ps:person=$pers -> meta:source +:time@=(2014,2017) -> geo:place',
    'ps:person=$pers -> meta:source -> *',
    'ps:person=$pers -> meta:source :node -> *',
    'reindex --form-counts',
    'sudo | [ inet:ipv4=1.2.3.4 ]',
    'sudo | [ test:cycle0=foo :test:cycle1=bar ]',
    'sudo | [ test:guid="*" ]',
    'sudo | [ test:str=foo +#lol ]',
    'sudo | [ test:str=foo ]',
    'sudo | [test:str=123 :tick=2018]',
    'sudo | test:int=6 | delnode',
    'syn:tag=a.b +#foo',
    'syn:tag=aaa.barbarella.ddd',
    'syn:tag=baz.faz [ +#foo.bar ]',
    'syn:tag=foo.bar -> *',
    'syn:tag=foo.bar -> test:str',
    'syn:tag=foo.bar -> test:str:tick',
    'test:comp +(:hehe<2 and :haha=test)',
    'test:comp +(:hehe<2 or #meep.gorp)',
    'test:comp +(:hehe<2 or :haha=test)',
    'test:comp +:haha*range=(grinch, meanone)',
    'test:comp +test:comp*range=((1024, grinch), (4096, zemeanone))',
    'test:comp -> * | uniq | count',
    'test:comp -> *',
    'test:comp -> test:int',
    'test:comp:haha~="^lulz"',
    'test:comp:haha~="^zerg"',
    'test:comp#bar +:hehe=1010 +:haha=test10 +#bar',
    'test:guid +test:guid*range=(abcd, dcbe)',
    'test:guid | max tick',
    'test:guid | min tick',
    'test:int +:loc=""',
    'test:int +:loc="us.va. syria"',
    'test:int +:loc=u',
    'test:int +:loc=us',
    'test:int +:loc=us.v',
    'test:int +:loc=us.va.sydney',
    'test:int +:loc^=""',
    'test:int +:loc^=23',
    'test:int +:loc^=u',
    'test:int +:loc^=us',
    'test:int +:loc^=us.',
    'test:int +:loc^=us.va.',
    'test:int +:loc^=us.va.fairfax.reston',
    'test:int +test:int<30',
    'test:int +test:int<=30',
    'test:int <=20',
    'test:int | noderefs | +test:comp*range=((1000, grinch), (4000, whoville))',
    'test:int:loc=""',
    'test:int:loc=u',
    'test:int:loc=us',
    'test:int:loc^=""',
    'test:int:loc^=23',
    'test:int:loc^=u',
    'test:int:loc^=us',
    'test:int:loc^=us.',
    'test:int:loc^=us.va.fairfax.reston',
    'test:int<30',
    'test:int<=30',
    'test:int=123 | noderefs -te',
    'test:int=123 | noderefs',
    'test:int=1234 [test:str=$node.form()] -test:int',
    'test:int=1234 [test:str=$node.value()] -test:int',
    'test:int=3735928559',
    'test:int=8675309',
    'test:int>30',
    'test:int>=20',
    'test:pivcomp -> test:int',
    'test:pivcomp | noderefs --join --degrees 2',
    'test:pivcomp | noderefs --join -d 3',
    'test:pivcomp | noderefs --join',
    'test:pivcomp | noderefs -j --degrees 2',
    'test:pivcomp | noderefs',
    'test:pivcomp:tick=$foo',
    'test:pivcomp=$foo',
    'test:pivcomp=(foo,bar) +{ :lulz -> test:str +#baz } +test:pivcomp',
    'test:pivcomp=(foo,bar) -+> *',
    'test:pivcomp=(foo,bar) -+> test:pivtarg',
    'test:pivcomp=(foo,bar) -> *',
    'test:pivcomp=(foo,bar) -> test:pivtarg',
    'test:pivcomp=(foo,bar) -{ :lulz -> test:str +#baz }',
    'test:pivcomp=(foo,bar) :lulz -+> test:str',
    'test:pivcomp=(foo,bar) :lulz -> test:str',
    'test:pivcomp=(foo,bar) :targ -> test:pivtarg',
    'test:pivcomp=(hehe,haha) $ticktock=#foo -> test:pivtarg +.seen@=$ticktock',
    'test:pivcomp=(hehe,haha)',
    'test:pivtarg=hehe [ .seen=2015 ]',
    'test:str +#*',
    'test:str +#**.bar.baz',
    'test:str +#**.baz',
    'test:str +#*.bad',
    'test:str +#foo.**.baz',
    'test:str +#foo.*.baz',
    '#foo@=("2013", "2015")',
    'test:str +#foo@=(2014, 20141231)',
    'test:str +#foo@=(2015, 2018)',
    'test:str +#foo@=2016',
    'test:str +:bar*range=((test:str, c), (test:str, q))',
    'test:str +:tick*range=(19701125, 20151212)',
    'test:str +:tick=($test, "+- 2day")',
    'test:str +:tick=(2015, "+1 day")',
    'test:str +:tick=(20150102, "-3 day")',
    'test:str +:tick=(20150201, "+1 day")',
    'test:str +:tick=2015',
    'test:str +:tick@="-1 day"',
    'test:str +:tick@=("now+2days", "-3 day")',
    'test:str +:tick@=("now-1day", "?")',
    'test:str +:tick@=2015',
    'test:str +:tick@=(2015, "+1 day")',
    'test:str +:tick@=(20150102+1day, "-4 day")',
    'test:str +:tick@=(20150102, "-4 day")',
    'test:str +:tick@=(now, "-1 day")',
    'test:str +test:str:tick<201808021202',
    'test:str +test:str:tick<=201808021202',
    'test:str +test:str:tick>201808021202',
    'test:str +test:str:tick>=201808021202',
    'test:str -#*',
    'test:str [+#foo.bar=(2000,2002)]',
    'test:str [+#foo.bar=(2000,20020601)]',
    'test:str [+#foo.bar]',
    'test:str [-#foo]',
    'test:str [-:tick]',
    'test:str | delnode --force',
    'test:str | noderefs -d 3 --unique',
    'test:str | noderefs -d 3',
    'test:str#foo',
    'test:str#foo.bar',
    'test:str#foo@=(2012,2022)',
    'test:str#foo@=2016',
    'test:str',
    'test:str:tick<201808021202',
    'test:str:tick<=201808021202',
    'test:str:tick=(20131231, "+2 days")',
    'test:str:tick=2015',
    'test:str:tick>201808021202',
    'test:str:tick>=201808021202',
    'test:str= foo',
    'test:str="foo bar" +test:str',
    'test:str="foo bar" -test:str:tick',
    'test:str="foo bar" [ -:tick ]',
    'test:str=$foo',
    'test:str=123 [:baz="test:guid:tick=2015"]',
    'test:str=123 | noderefs --traverse-edge',
    'test:str=123 | noderefs',
    'test:str=1234 test:str=duck test:str=knight',
    'test:str=a +:tick*range=(20000101, 20101201)',
    'test:str=bar -+> test:pivcomp:lulz',
    'test:str=bar -> test:pivcomp:lulz',
    'test:str=bar <+- *',
    'test:str=bar <- *',
    'test:str=bar test:pivcomp=(foo,bar) [+#test.bar]',
    'test:str=foo +#lol@=2016',
    'test:str=foo <+- meta:source',
    'test:str=foo <- meta:source',
    'test:str=foo | delnode',
    'test:str=foobar -+> meta:source',
    'test:str=foobar -> meta:source <+- test:str',
    'test:str=foobar -> meta:source <- test:str',
    'test:str=hello [:tick="2001"]',
    'test:str=hello [:tick="2002"]',
    'test:str=pennywise | noderefs --join -d 9 --traverse-edge',
    'test:str=pennywise | noderefs -d 3 --omit-traversal-tag=omit.nopiv --omit-traversal-tag=test',
    'test:str=visi -> #*',
    'test:str=visi -> #foo.*',
    'test:str=woot $foo=#foo +.seen@=$foo',
    'test:str=woot +.seen@=#bar',
    'test:str=woot +.seen@=(2012,2015)',
    'test:str=woot +.seen@=2012',
    'test:str~="zip"',
    '''
        for $foo in $foos {

            ($fqdn, $ipv4) = $foo.split("|")

            [ inet:dns:a=($fqdn, $ipv4) ]
        } ''',
    ''' /* A comment */ test:int ''',
    ''' test:int // a comment''',
    '''/* multi
         line */ test:int ''',
    '''
        inet:fqdn | graph
                    --degrees 2
                    --filter { -#nope }
                    --pivot { <- meta:source <- meta:source }
                    --form-pivot inet:fqdn {<- * | limit 20}
                    --form-pivot inet:fqdn {-> * | limit 20}
                    --form-filter inet:fqdn {-inet:fqdn:issuffix=1}
                    --form-pivot syn:tag {-> *}
                    --form-pivot * {-> #} ''',
    '''
        for $foo in $foos {

            ($fqdn, $ipv4) = $foo.split("|")

            [ inet:dns:a=($fqdn, $ipv4) ]
        } ''',
    '''
    for $tag in $node.tags() {
        -> test:int [ +#$tag ]
    } ''',
    '''
    for $tag in $node.tags(fo*) {
        -> test:int [ -#$tag ]
    }
    ''',
    '''
    [
    inet:email:message="*"
        :to=woot@woot.com
        :from=visi@vertex.link
        :replyto=root@root.com
        :subject="hi there"
        :date=2015
        :body="there are mad sploitz here!"
        :bytes="*"
    ]

    {[ inet:email:message:link=($node, https://www.vertex.link) ]}

    {[ inet:email:message:attachment=($node, "*") ] -inet:email:message [ :name=sploit.exe ]}

    {[ meta:source=($node, ('inet:email:header', ('to', 'Visi Kensho <visi@vertex.link>'))) ]}
    ''',
    '$x = $(1 / 3)',
    '$x = $(1 * 3)',
    '$x = $(1 * 3 + 2)',
    '$x = $(1 -3.2 / -3.2)',
    '$x = $(1 + 3 / 2    )',
    '$x = $((1 + 3)/ 2)',
    '$x = (2 ** 4)',
    '$x = (2 % 4)',
    '$x = (5 + 100 % 3)',
    '$x = (5 - 100 % 3)',
    '$x = (5 * 100 % 3)',
    '$x = (5 / 100 % 3)',

    # This group of expressions is for checking the lookaheads in the NUMBER.1,
    # HEXNUMBER.1, and OCTNUMBER.1 regular expressions in storm.lark. These two regexes allow
    # for no spaces between the numbers and the operators (+-*/%)
    '$x = (5+100%3)',
    '$x = (5-100%3)',
    '$x = (5*100%3)',
    '$x = (5/100%3)',
    '$x = (0x5+0x100%0x3)',
    '$x = (0x5-0x100%0x3)',
    '$x = (0x5*0x100%0x3)',
    '$x = (0x5/0x100%0x3)',
    '$x = (0o5+0o100%0o3)',
    '$x = (0o5-0o100%0o3)',
    '$x = (0o5*0o100%0o3)',
    '$x = (0o5/0o100%0o3)',

    '$foo=42 $foo2=43 $x = $($foo * $foo2)',
    '$yep=$(42 < 43)',
    '$yep=$(42 > 43)',
    '$yep=$(42 >= 43)',
    '$yep=$(42 + 4 <= 43 * 43)',
    '$foo=4.3 $bar=4.2 $baz=$($foo + $bar)',
    'inet:ipv4=1 $foo=.created $bar=$($foo +1 )',
    "$x=$($lib.time.offset('2 days'))",
    '$foo = 1 $bar = 2 inet:ipv4=$($foo + $bar)',
    '',
    'hehe.haha --size 10 --query "foo_bar.stuff:baz"',
    'if $foo {[+#woot]}',
    'if $foo {[+#woot]} else {[+#nowoot]}',
    'if $foo {[+#woot]} elif $(1-1) {[+#nowoot]}',
    'if $foo {[+#woot]} elif $(1-1) {[+#nowoot]} else {[+#nonowoot] }',
    'if ($data ~= "hehe") {$lib.print(yes)} else {$lib.print(no)}',
    '$foo=$(1 or 0 and 0)',
    '$foo=$(not 1 and 1)',
    '$foo=$(not 1 > 1)',
    '#baz.faz:lol',
    'foo:bar#baz.faz:lol',
    '#baz.faz:lol=20',
    'foo:bar#baz.faz:lol=20',
    '+#foo.bar:lol',
    '+#foo.bar:lol=20',
    '[ -#baz.faz:lol ]',
    '[ +#baz.faz:lol=20 ]',
    '#tag:somegeoloctypebecauseihatelife*near=($lat, $long)',
    '*$foo*near=20',
    '[ test:str = $foo.woot.var.$bar.mar.$car ]',
    'test:str = $foo.$\'space key\'.subkey',
    '''
    for $iterkey in $foo.$"bar key".$\'biz key\' {
        inet:ipv4=$foo.$"bar key".$\'biz key\'.$iterkey
    }
    ''',
    ''' [(ou:org=c71cd602f73af5bed208da21012fdf54 :loc=us )]''',
    'function x(y, z) { return ($( $x - $y ) ) }',
    'function echo(arg, arg2=default) { return ($arg) }',
    '$name = asdf $foo = ({}) $foo.bar = asdf $foo."bar baz" = asdf $foo.$name = asdf',
    '[test:str=a] switch $node.form() { hehe: {[+#baz]} }',
    '[test:str=a] switch $woot { hehe: {[+#baz]} }',
    '[test:str=c] switch $woot { hehe: {[+#baz]} *: {[+#jaz]} }',
    '[test:str=c] switch $woot { hehe: {[+#baz]} "haha hoho": {[+#faz]} "lolz:lulz": {[+#jaz]} }',
    '''
        /* A
            multiline
            comment */
        [ inet:ipv4=1.2.3.4 ] // this is a comment
        // and this too...

        switch $foo {

            // The bar case...

            bar: {
                [ +#hehe.haha ]
            }

            /*
                The
                baz
                case
            */
            'baz faz': {}
        } ''',
    '''
        for $foo in $foos {

            [ inet:ipv4=1.2.3.4 ]

            switch $foo {
                bar: { [ +#ohai ] break }
                baz: { [ +#visi ] continue }
                (far, faz): { [ +#multi.far ] continue }
                ("gar", "gaz"): { [ +#multi.gar ] continue }
                ('har', 'haz'): { [ +#multi.har ] continue }
                ("kar", 'kaz', koo): { [ +#multi.kar ] continue }
            }

            [ inet:ipv4=5.6.7.8 ]
            [ +#hehe ]
        } ''',
    'switch $a { "a": { } }',
    'switch $a { "test:str" : { } *: {}}',
    'switch $a { "test:this:works:" : { } * : {}}',
    '''switch $a { 'single:quotes' : { } "doubele:quotes": {} noquotes: { } * : {}}''',
    'switch $category { } switch $type { *: { } }',
    'syn:tag -+> #',
    'syn:tag:base -+> #',
    'syn:tag:base=foo -+> #',
    'syn:tag:depth=2 -+> #',
    'inet:ipv4 -+> #',
    'inet:ipv4 -+> #*',
    'inet:ipv4=1.2.3.4 -+> #',
    'inet:ipv4=1.2.3.4 -+> #*',
    'inet:ipv4=1.2.3.4 -+> #biz.*',
    'inet:ipv4=1.2.3.4 -+> #bar.baz',
    'function middlechild(arg2) { yield $rockbottom($arg2) }',
    '[test:comp=(10,bar)] yield { -> test:int}',
    'test:arrayprop +:ints*[ range=(50,100) ]',
    'inet:ipv4 +(($foo and $bar))',
    'inet:ipv4 +($(0 and 1))',
    '$x=$($x-1)',
    'inet:ipv4=1.2.3.4 +$(:asn + 20 >= 42)',
    'inet:ipv4 -(seen)> foo:bar:baz',
    'inet:ipv4 -(seen)> (foo:bar:baz, hehe:haha:hoho)^=lol',
    'inet:ipv4 -(($foo, $bar))> ($baz,$faz)=lol',
    '$x=(["foo", "bar"])',
    '$x=(["foo", "bar",])',
    '$x=({"foo": "bar", "baz": 10})',
    '$x=({"foo": "bar", "baz": 10, })',
    'iden ssl://svcrs:27492?certname=root=bar',
    '$x=(foo bar baz, two)',
    '''$foo=`foo
    bar`''',
    '$foo=(truesec.com,)',
    '[test:str=foo +#$tag.index(0):$tag.index(1)=$tag.index(2)]',
    'test:str#$tag.index(0):$tag.index(1)',
    'if $lib.true { } $lib.print(`User: {$lib.true}`)',
    '$foo.`{$bar.baz}`=$bar',
    '$foo.`{$bar.baz}` = $bar',
    '$foo.($bar.baz)=$bar',
    '$foo.($bar.baz) = $bar',
    '$lib.print($foo.`{$bar.baz}`)',
    '$lib.print($foo.($bar.baz))',
    "$lib.print($a.('foo').upper())",
    "$lib.print(($a.('foo').upper()))",
    "$lib.print($a.$('foo').upper())",
    "$lib.print(($a.$('foo').upper()))",
    "$lib.print(('foo').upper())",
    "$lib.print((('foo').upper()))",
    '$lib.print(($foo)())',
    '$lib.print((($foo)()))',
    '$lib.print((:prop).upper())',
    '$lib.print(((:prop).upper()))',
    "$lib.print(({'unicode': 1}).(:prop))",
    "$lib.print((({'unicode': 1}).(:prop)+(2)))",
    '*$form#$tag',
    '*$form#$tag:$prop',
    'reverse(inet:ipv4)',
    'reverse(inet:ipv4=1.2.3.4)',
    'reverse(*$form=$valu)',
    'test:str=foobar -> inet:dns*',
    'test:str=foobar -> inet:dns:*',
    'test:str=foobar -> (meta:source, inet:dns:a)',
    'test:str=foobar -> (meta:source, inet:dns*)',
    'test:str=foobar -> $foo',
    'test:str=foobar -+> inet:dns*',
    'test:str=foobar -+> inet:dns:*',
    'test:str=foobar -+> (meta:source, inet:dns:a)',
    'test:str=foobar -+> (meta:source, inet:dns*)',
    'test:str=foobar -+> $foo',
    'test:str=foobar -(refs)> inet:dns:*',
    'inet:fqdn=foo.com :zone -> (meta:source, inet:dns:a)',
    'inet:fqdn=foo.com :zone -> $foo',
    'inet:fqdn=foo.com :zone -+> (meta:source, inet:dns:a)',
    'inet:fqdn=foo.com :zone -+> $foo',
    'test:*#foo',
    'test:*#foo@=2016',
    'test:*#foo:lol',
    'test:*#foo:lol=20',
    '.created +inet:dns*',
    '.created -inet:dns*',
    '.created +inet:dns:*',
    '.created -inet:dns:*',
    'inet:ipv4 --+> *',
    'file:bytes <+-- *',
    'inet:asn <+("edge")- *',
    'inet:asn -("edge")+> *',
    'file:bytes -(($foobar, $bizbaz))+> ($biz, $boz)=lol',
    'media:news <+((neato, burrito))- inet:fqdn',
    'inet:ipv4 <+(*)- media:news',
    'media:news -(*)+> inet:fqdn',
    'inet:ipv4 <+(*)- *',
    'media:news -(*)+> *',
    '$foo=(null)',
    '$foo=({"bar": null})',
    '$p="names" ps:contact:name=foo [ :$p?+=bar ]',
    '$p="names" ps:contact:name=foo [ :$p?-=bar ]',
    '$pvar=stuff test:arrayprop +:$pvar*[=neato]',
    '$pvar=ints test:arrayprop +:$pvar*[=$othervar]',
    '$foo = ({"foo": ${ inet:fqdn }})',
    '[test:str=foo :hehe*unset=heval]',
    '[test:str=foo :hehe*$foo=heval]',
    '[test:str=foo :$foo*unset=heval]',
    '[test:str=foo :$foo*$bar=heval]',
    '[test:str=foo :$foo*$bar.baz=heval]',
    '[test:str=foo :$foo*$bar.("baz")=heval]',
    '[test:str=foo :$foo*$bar.baz()=heval]',
    '[test:str=foo +(refs)> $n]',
    '[test:str=foo +(refs)> $n.baz()]',
    '[test:str=foo -(refs)> $n]',
    '[test:str=foo <(refs)+ $n]',
    '[test:str=foo <(refs)+ $n.baz()]',
    '[test:str=foo <(refs)- $n]',
    '[test:str=foo :bar++=([1, 2])]',
    '[test:str=foo :$foo++=([1, 2])]',
    '[test:str=foo :bar--=(foo, bar)]',
    '[test:str=foo :bar?++=$baz]',
    '[test:str=foo :bar?--={[it:dev:str=foo]}]',
    '$foo=(notime,)',
    '$foo=(nulltime,)',
    '$foo=(not$x)',
    '$foo=(not $x)',
    '$foo=(not($x))',
    '$foo=(not ($x))',
]

# Generated with print_parse_list below
_ParseResults = [
    'Query: [SetVarOper: [Const: foo, DollarExpr: [UnaryExprNode: [Const: -, VarValue: [Const: foo]]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [UnaryExprNode: [Const: -, TagValue: [TagName: [Const: foo]]]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [UnaryExprNode: [Const: -, UnivPropValue: [Const: .foo]]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [UnaryExprNode: [Const: -, RelPropValue: [Const: foo]]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [UnaryExprNode: [Const: -, DollarExpr: [ExprNode: [VarValue: [Const: foo], Const: -, Const: 1]]]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [UnaryExprNode: [Const: -, UnaryExprNode: [Const: -, VarValue: [Const: foo]]]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [ExprNode: [Const: 5, Const: -, UnaryExprNode: [Const: -, UnaryExprNode: [Const: -, VarValue: [Const: foo]]]]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [ExprNode: [Const: 5, Const: +, UnaryExprNode: [Const: -, VarValue: [Const: foo]]]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [ExprNode: [Const: 5, Const: +, UnaryExprNode: [Const: -, UnaryExprNode: [Const: -, VarValue: [Const: foo]]]]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [TagPropValue: [TagProp: [TagName: [VarValue: [Const: tag]], VarValue: [Const: tagprop]]]]]]',
    'Query: [LiftTagProp: [TagProp: [TagName: [VarValue: [Const: tag]], VarValue: [Const: tagprop]]]]',
    'Query: [LiftTagProp: [TagProp: [TagName: [VarValue: [Const: tag]], VarValue: [Const: tagprop]], Const: =, VarValue: [Const: valu]]]',
    'Query: [EditTagPropSet: [TagProp: [TagName: [VarValue: [Const: tag]], VarValue: [Const: tagprop]], Const: =, VarValue: [Const: valu]]]',
    'Query: [VarEvalOper: [FuncCall: [VarDeref: [VarValue: [Const: lib], Const: print], CallArgs: [FormatString: [Const: ip=, FuncCall: [VarDeref: [VarValue: [Const: node], Const: repr], CallArgs: [], CallKwargs: []], Const:  asn=, RelPropValue: [Const: asn], Const:  .seen=, UnivPropValue: [Const: .seen], Const:  foo=, TagValue: [TagName: [Const: foo]], Const:  , ExprNode: [RelPropValue: [Const: asn], Const: =, Const: 5]]], CallKwargs: []]]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 45.79.131.138], FormPivot: [Const: inet:flow], isjoin=False, FiltOper: [Const: -, OrCond: [RelPropCond: [RelPropValue: [RelProp: [Const: dst:port]], Const: =, Const: 444], RelPropCond: [RelPropValue: [RelProp: [Const: dst:port]], Const: =, Const: 80]]]]',
    'Query: [LiftPropBy: [Const: media:news, Const: =, Const: 0c7f7267d3b62432cb0d7d0e9d3108a4], N1Walk: [Const: refs, Const: inet:ipv4], isjoin=False]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [Const: 2]], Return: [DollarExpr: [ExprNode: [VarValue: [Const: foo], Const: +, DollarExpr: [Const: 1]]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [Const: 2]], Return: [DollarExpr: [ExprNode: [VarValue: [Const: foo], Const: -, DollarExpr: [Const: 1]]]]]',
    'Query: [Return: [DollarExpr: [ExprNode: [DollarExpr: [Const: 2], Const: +, DollarExpr: [Const: 1]]]]]',
    'Query: [Return: [DollarExpr: [ExprNode: [DollarExpr: [Const: 2], Const: -, DollarExpr: [Const: 1]]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [Const: 2]], Return: [DollarExpr: [ExprNode: [VarValue: [Const: foo], Const: <, DollarExpr: [Const: 3]]]]]',
    'Query: [Return: [DollarExpr: [ExprNode: [DollarExpr: [Const: 2], Const: <, DollarExpr: [Const: 3]]]]]',
    'Query: [Return: [DollarExpr: [ExprNode: [DollarExpr: [Const: 1], Const: <, ExprNode: [DollarExpr: [Const: 3], Const: -, DollarExpr: [Const: 1]]]]]]',
    'Query: [Return: [DollarExpr: [ExprNode: [DollarExpr: [Const: 1], Const: <, ExprNode: [DollarExpr: [Const: 3], Const: -, DollarExpr: [Const: 1]]]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [Const: 2]], Return: [DollarExpr: [ExprNode: [VarValue: [Const: foo], Const: <, ExprNode: [DollarExpr: [Const: 4], Const: -, DollarExpr: [Const: 1]]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 1.2.3.4], EditPropSet: [RelProp: [Const: asn], Const: =, Const: 1], Return: [DollarExpr: [ExprNode: [RelPropValue: [Const: asn], Const: <, ExprNode: [DollarExpr: [Const: 4], Const: -, DollarExpr: [Const: 1]]]]]]',
    'Query: [SetVarOper: [Const: p, Const: asn], LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.4], Return: [DollarExpr: [ExprNode: [RelPropValue: [VarValue: [Const: p]], Const: <, ExprNode: [DollarExpr: [Const: 4], Const: -, DollarExpr: [Const: 1]]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 1.2.3.4], EditPropSet: [UnivProp: [Const: .test:univ], Const: =, Const: 0], Return: [DollarExpr: [ExprNode: [UnivPropValue: [Const: .test:univ], Const: <, ExprNode: [DollarExpr: [Const: 4], Const: -, DollarExpr: [Const: 1]]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 1.2.3.4], EditTagPropSet: [TagProp: [TagName: [Const: foo], Const: score], Const: =, Const: 1], Return: [DollarExpr: [ExprNode: [TagPropValue: [TagProp: [TagName: [Const: foo], Const: score]], Const: <, ExprNode: [DollarExpr: [Const: 4], Const: -, DollarExpr: [Const: 1]]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 1.2.3.4], EditTagAdd: [TagName: [Const: foo], Const: =, DollarExpr: [Const: 0]], Return: [DollarExpr: [ExprNode: [TagValue: [TagName: [Const: foo]], Const: <, ExprNode: [DollarExpr: [Const: 4], Const: -, DollarExpr: [Const: 1]]]]]]',
    'Query: [SetVarOper: [Const: p, Const: bar], EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 1.2.3.4], EditTagAdd: [TagName: [Const: foo, Const: bar], Const: =, DollarExpr: [Const: 0]], Return: [DollarExpr: [ExprNode: [TagValue: [TagName: [Const: foo, VarValue: [Const: p]]], Const: <, ExprNode: [DollarExpr: [Const: 4], Const: -, DollarExpr: [Const: 1]]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:asn], Const: =, Const: 1], EditNodeAdd: [FormName: [Const: inet:asn], Const: =, Const: 2], EditEdgeAdd: [Const: foo), SubQuery: [Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.4]]]]]',
    'Query: [LiftPropBy: [Const: inet:asn, Const: <, DollarExpr: [Const: 2]]]',
    'Query: [LiftProp: [Const: inet:asn], N2Walk: [Const: foo), Const: *], isjoin=False]',
    'Query: [LiftProp: [Const: inet:asn], N2Walk: [List: [Const: foo), Const: bar()], Const: *], isjoin=False]',
    'Query: [Emit: [VarValue: [Const: foo]], Stop: []]',
    'Query: [TryCatch: [Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: asdf]], CatchBlock: [Const: TypeError, Const: err, Query: []]]]',
    'Query: [TryCatch: [Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: asdf]], CatchBlock: [Const: FooBar, Const: err, Query: []], CatchBlock: [Const: *, Const: err, Query: []]]]',
    'Query: [LiftByArray: [Const: test:array, Const: =, Const: 1.2.3.4]]',
    'Query: [CmdOper: [Const: macro.set, List: [Const: hehe, EmbedQuery:  inet:ipv4 ]]]',
    'Query: [SetVarOper: [Const: q, EmbedQuery: #foo.bar]]',
    'Query: [CmdOper: [Const: metrics.edits.byprop, List: [Const: inet:fqdn:domain, Const: --newv, VarDeref: [VarValue: [Const: lib], Const: null]]]]',
    'Query: [CmdOper: [Const: tee, Const: ()]]',
    'Query: [LiftPropBy: [Const: inet:fqdn, Const: =, Const: newp.com], CmdOper: [Const: tee, List: [ArgvQuery: [Query: [LiftProp: [Const: inet:fqdn]]]]], CmdOper: [Const: uniq, Const: ()]]',
    'Query: [LiftPropBy: [Const: inet:fqdn, Const: =, Const: newp.com], CmdOper: [Const: tee, List: [ArgvQuery: [Query: [LiftProp: [Const: inet:fqdn]]]]], CmdOper: [Const: uniq, Const: ()]]',
    'Query: [CmdOper: [Const: hehe.haha, List: [Const: foo]]]',
    'Query: [LiftProp: [Const: inet:ipv4], N1WalkNPivo: [], isjoin=False]',
    'Query: [LiftProp: [Const: inet:ipv4], N2WalkNPivo: [], isjoin=False]',
    'Query: [LiftPropBy: [Const: inet:fqdn, Const: =, Const: woot.com], EditEdgeAdd: [Const: refs, SubQuery: [Query: [LiftProp: [Const: media:news]]]]]',
    'Query: [LiftPropBy: [Const: inet:fqdn, Const: =, Const: woot.com], EditEdgeAdd: [Const: refs, SubQuery: [Query: [LiftProp: [Const: media:news]]]]]',
    'Query: [SetVarOper: [Const: refs, Const: refs], LiftProp: [Const: media:news], N1Walk: [VarValue: [Const: refs], Const: *], isjoin=False, FiltOper: [Const: -, OrCond: [TagCond: [TagMatch: [Const: foo]], TagCond: [TagMatch: [Const: bar]]]]]',
    'Query: [SetVarOper: [Const: refs, Const: refs], LiftProp: [Const: media:news], N2Walk: [VarValue: [Const: refs], List: [Const: inet:ipv4, Const: inet:ipv6]], isjoin=False, FiltOper: [Const: -, OrCond: [TagCond: [TagMatch: [Const: foo]], TagCond: [TagMatch: [Const: bar]]]]]',
    'Query: [LiftProp: [Const: media:news], N1Walk: [Const: refs, Const: *], isjoin=False, FiltOper: [Const: -, OrCond: [TagCond: [TagMatch: [Const: foo]], TagCond: [TagMatch: [Const: bar]]]]]',
    'Query: [LiftProp: [Const: media:news], N2Walk: [Const: refs, VarValue: [Const: bar]], isjoin=False, FiltOper: [Const: -, OrCond: [TagCond: [TagMatch: [Const: foo]], TagCond: [TagMatch: [Const: bar]]]]]',
    'Query: [LiftProp: [Const: media:news], EditEdgeDel: [Const: refs, SubQuery: [Query: [LiftPropBy: [Const: inet:fqdn, Const: =, Const: woot.com]]]]]',
    'Query: [LiftProp: [Const: media:news], EditEdgeAdd: [Const: refs, SubQuery: [Query: [LiftPropBy: [Const: inet:fqdn, Const: =, Const: woot.com]]]]]',
    'Query: [CmdOper: [Const: cron, List: [Const: add, Const: --monthly, Const: -1:12:30, ArgvQuery: [Query: [LiftTag: [TagName: [Const: bar]]]]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [ExprOrNode: [ExprOrNode: [Const: 1, Const: or, Const: 1], Const: or, Const: 0]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [ExprAndNode: [ExprAndNode: [Const: 1, Const: and, Const: 1], Const: and, Const: 0]]]]',
    'Query: [SetVarOper: [Const: var, Const: tag1], LiftTag: [TagName: [Const: base, VarValue: [Const: var]]]]',
    'Query: [LiftProp: [Const: test:str], SetVarOper: [Const: var, Const: tag1], FiltOper: [Const: +, TagValuCond: [TagMatch: [Const: base, VarValue: [Const: var]], Const: @=, Const: 2014]]]',
    'Query: [LiftProp: [Const: test:str], SetVarOper: [Const: var, Const: tag1], PivotToTags: [TagMatch: [Const: base, VarValue: [Const: var]]], isjoin=False]',
    'Query: [SetVarOper: [Const: var, Const: hehe], EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditPropSet: [RelProp: [VarValue: [Const: var]], Const: =, Const: heval]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: heval], LiftProp: [Const: test:str], SetVarOper: [Const: var, Const: hehe], FiltOper: [Const: +, HasRelPropCond: [RelProp: [VarValue: [Const: var]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditPropSet: [RelProp: [Const: tick], Const: =, Const: 2019], SetVarOper: [Const: var, Const: tick], EditPropDel: [RelProp: [VarValue: [Const: var]]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo], SetVarOper: [Const: var, Const: hehe], PropPivot: [RelPropValue: [RelProp: [VarValue: [Const: var]]], Const: test:str], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo], SetVarOper: [Const: var, Const: seen], EditPropSet: [UnivProp: [VarValue: [Const: var]], Const: =, Const: 2019]]',
    'Query: [LiftProp: [Const: test:str], SetVarOper: [Const: var, Const: seen], FiltOper: [Const: +, HasRelPropCond: [UnivProp: [VarValue: [Const: var]]]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo], SetVarOper: [Const: var, Const: seen], EditUnivDel: [UnivProp: [VarValue: [Const: var]]], CmdOper: [Const: spin, Const: ()], LiftPropBy: [Const: test:str, Const: =, Const: foo]]',
    'Query: [SetVarOper: [Const: var, Const: hehe], EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditPropSet: [RelProp: [VarValue: [Const: hehe]], Const: =, Const: heval]]',
    'Query: [LiftTag: [TagName: [Const: tag, VarValue: [Const: bar]]]]',
    'Query: [FiltOper: [Const: +, TagCond: [TagMatch: [Const: tag, VarValue: [Const: bar]]]]]',
    'Query: [FiltOper: [Const: +, TagCond: [TagMatch: [Const: tag, VarValue: [Const: bar], Const: *]]]]',
    'Query: [LiftTag: [TagName: [Const: tag, VarValue: [Const: escaped "string"]]]]',
    'Query: [FiltOper: [Const: +, TagCond: [TagMatch: [Const: tag, VarValue: [Const: escaped "string"], Const: *]]]]',
    'Query: [EditTagAdd: [TagName: [Const: tag, VarValue: [Const: escaped "string"]]]]',
    'Query: [LiftProp: [Const: test:str], SetVarOper: [Const: some\x08var, FuncCall: [VarDeref: [VarValue: [Const: node], Const: repr], CallArgs: [], CallKwargs: []]]]',
    'Query: [SetVarOper: [Const: x, Const: 0], WhileLoop: [DollarExpr: [ExprNode: [VarValue: [Const: x], Const: <, Const: 10]], SubQuery: [Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [VarValue: [Const: x], Const: +, Const: 1]]], EditNodeAdd: [FormName: [Const: test:int], Const: =, VarValue: [Const: x]]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:int], Const: ?=, Const: 4], EditNodeAdd: [FormName: [Const: test:int], Const: ?=, Const: nonono]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:int], Const: =, Const: 4], EditTagAdd: [Const: ?, TagName: [Const: hehe, Const: haha]], EditTagAdd: [Const: ?, TagName: [Const: hehe, Const: newp], Const: =, Const: newp], EditTagAdd: [TagName: [Const: hehe, Const: yes], Const: =, Const: 2020]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditPropSet: [RelProp: [Const: tick], Const: ?=, Const: 2019]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: a], SwitchCase: [FuncCall: [VarDeref: [VarValue: [Const: node], Const: form], CallArgs: [], CallKwargs: []], CaseEntry: [Const: hehe, SubQuery: [Query: [EditTagAdd: [TagName: [Const: baz]]]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:type10], Const: =, Const: 2], EditPropSet: [RelProp: [Const: strprop], Const: =, Const: 1], CmdOper: [Const: spin, Const: ()], LiftProp: [Const: test:type10], FiltOper: [Const: +, DollarExpr: [RelPropValue: [Const: strprop]]], SetVarOper: [Const: foo, Const: 1], FiltOper: [Const: +, VarValue: [Const: foo]]]',
    'Query: [LiftFormTag: [Const: inet:fqdn, TagName: [Const: xxx, Const: xxxxxx, Const: xxxx, Const: xx]], ForLoop: [Const: tag, FuncCall: [VarDeref: [VarValue: [Const: node], Const: tags], CallArgs: [Const: xxx.xxxxxx.*.xx], CallKwargs: []], SubQuery: [Query: [PivotInFrom: [Const: inet:dns:a], isjoin=False, FiltOper: [Const: +, TagCond: [TagMatch: [Const: xx]]], PivotInFrom: [Const: meta:note], isjoin=False, EditTagAdd: [TagName: [Const: foo]], FormPivot: [Const: inet:dns:a], isjoin=False]]]]',
    'Query: [FiltOper: [Const: +, AbsPropCond: [Const: syn:tag, Const: ~=, Const: aka.*.mal.*]]]',
    'Query: [FiltOper: [Const: +, OrCond: [OrCond: [AbsPropCond: [Const: syn:tag, Const: ^=, Const: aka], AbsPropCond: [Const: syn:tag, Const: ^=, Const: cno]], AbsPropCond: [Const: syn:tag, Const: ^=, Const: rep]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditNodeAdd: [FormName: [Const: test:int], Const: =, Const: 42]]',
    'Query: [CmdOper: [Const: help, Const: ()]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: abcd], EditPropSet: [RelProp: [Const: tick], Const: =, Const: 2015], EditTagAdd: [TagName: [Const: cool]]]',
    'Query: [SubQuery: [Query: [LiftTag: [TagName: [Const: baz]]]], LiftPropBy: [Const: test:str, Const: =, Const: foo]]',
    'Query: [LiftTagTag: [TagName: [Const: baz, Const: faz]]]',
    'Query: [LiftTag: [TagName: [VarValue: [Const: tag]]], EditTagDel: [TagName: [VarValue: [Const: tag]]]]',
    'Query: [LiftTag: [TagName: [VarValue: [Const: tag]]]]',
    'Query: [LiftTag: [TagName: [Const: foo]]]',
    'Query: [LiftTag: [TagName: [Const: foo]]]',
    'Query: [LiftTag: [TagName: [Const: foo]]]',
    'Query: [LiftTag: [TagName: [Const: hehe, Const: haha]]]',
    'Query: [VarEvalOper: [VarDeref: [VarValue: [Const: hehe], Const: haha]]]',
    'Query: [LiftTag: [TagName: [Const: test, Const: bar]], FiltOper: [Const: +, HasAbsPropCond: [Const: test:pivcomp]], PivotOut: [], isjoin=True]',
    'Query: [LiftTag: [TagName: [Const: test, Const: bar]], FiltOper: [Const: +, HasAbsPropCond: [Const: test:pivcomp]], PivotOut: [], isjoin=False]',
    'Query: [LiftTag: [TagName: [Const: test, Const: bar]], FiltOper: [Const: +, HasAbsPropCond: [Const: test:str]], PivotIn: [], isjoin=True]',
    'Query: [LiftTag: [TagName: [Const: test, Const: bar]], FiltOper: [Const: +, HasAbsPropCond: [Const: test:str]], PivotIn: [], isjoin=False]',
    'Query: [LiftProp: [Const: test:migr], PivotInFrom: [Const: meta:note], isjoin=False]',
    'Query: [LiftTag: [TagName: [Const: test, Const: bar]], FiltOper: [Const: -, TagCond: [TagMatch: [Const: test]]], PivotOut: [], isjoin=True]',
    'Query: [LiftTag: [TagName: [Const: test, Const: bar]], FiltOper: [Const: -, TagCond: [TagMatch: [Const: test]]], PivotOut: [], isjoin=False]',
    'Query: [LiftTag: [TagName: [Const: test, Const: bar]], FiltOper: [Const: -, TagCond: [TagMatch: [Const: test]]], PivotIn: [], isjoin=True]',
    'Query: [LiftTag: [TagName: [Const: test, Const: bar]], FiltOper: [Const: -, TagCond: [TagMatch: [Const: test]]], PivotIn: [], isjoin=False]',
    'Query: [SetVarOper: [Const: bar, Const: 5.5.5.5], EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, VarValue: [Const: bar]]]',
    'Query: [SetVarOper: [Const: blah, DollarExpr: [ExprDict: [Const: foo, Const: vertex.link]]], EditNodeAdd: [FormName: [Const: inet:fqdn], Const: =, VarDeref: [VarValue: [Const: blah], Const: foo]]]',
    "Query: [VarListSetOper: [VarList: ['tick', 'tock'], UnivPropValue: [UnivProp: [Const: .seen]]]]",
    'Query: [LiftProp: [Const: .created]]',
    'Query: [LiftPropBy: [Const: .created, Const: <, Const: 2010]]',
    'Query: [LiftPropBy: [Const: .created, Const: >, Const: 2010]]',
    'Query: [LiftPropBy: [Const: .created, Const: range=, List: [Const: 2010, Const: ?]]]',
    'Query: [LiftPropBy: [Const: .created, Const: range=, List: [Const: 2010, Const: 3001]]]',
    'Query: [LiftPropBy: [Const: .created, Const: =, Const: 2001]]',
    'Query: [LiftPropBy: [Const: .created, Const: =, Const: {created}]]',
    'Query: [LiftProp: [Const: .seen], EditUnivDel: [UnivProp: [Const: .seen]]]',
    'Query: [LiftPropBy: [Const: .seen, Const: ~=, Const: ^r]]',
    'Query: [EditNodeAdd: [FormName: [Const: meta:note], Const: =, Const: *], EditPropSet: [RelProp: [Const: type], Const: =, Const: m1]]',
    'Query: [EditNodeAdd: [FormName: [Const: geo:place], Const: =, Const: *], EditPropSet: [RelProp: [Const: latlong], Const: =, List: [Const: -30.0, Const: 20.22]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:asn], Const: =, Const: 200], EditPropSet: [RelProp: [Const: name], Const: =, Const: visi]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:dns:a], Const: =, List: [Const: woot.com, Const: 12.34.56.78]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:dns:a], Const: =, FuncCall: [VarDeref: [VarValue: [Const: blob], Const: split], CallArgs: [Const: |], CallKwargs: []]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:dns:a], Const: =, List: [Const: vertex.link, Const: 5.5.5.5]], EditTagAdd: [TagName: [Const: nope]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:dns:a], Const: =, List: [Const: woot.com, Const: 1.2.3.4]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:dns:a], Const: =, List: [Const: woot.com, Const: 1.2.3.4]], EditTagAdd: [TagName: [Const: yepr]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:dns:a], Const: =, List: [Const: woot.com, Const: 1.2.3.4]], EditNodeAdd: [FormName: [Const: inet:dns:a], Const: =, List: [Const: vertex.link, Const: 1.2.3.4]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:dns:a], Const: =, List: [Const: woot.com, Const: 1.2.3.4]], EditPropSet: [UnivProp: [Const: .seen], Const: =, List: [Const: 2015, Const: 2016]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:fqdn], Const: =, Const: hehe.com], EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 127.0.0.1], EditNodeAdd: [FormName: [Const: hash:md5], Const: =, Const: d41d8cd98f00b204e9800998ecf8427e]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:fqdn], Const: =, Const: woot.com]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:fqdn], Const: =, Const: vertex.link], EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 1.2.3.4]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:fqdn], Const: =, Const: woot.com], EditTagAdd: [TagName: [Const: bad], Const: =, List: [Const: 2015, Const: 2016]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:fqdn], Const: =, Const: woot.com], PivotOut: [], isjoin=False]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:fqdn], Const: =, Const: woot.com], EditNodeAdd: [FormName: [Const: inet:fqdn], Const: =, Const: vertex.link], EditNodeAdd: [FormName: [Const: inet:user], Const: =, RelPropValue: [Const: zone]], FiltOper: [Const: +, HasAbsPropCond: [Const: inet:user]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 94.75.194.194], EditPropSet: [RelProp: [Const: loc], Const: =, Const: nl]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, VarValue: [Const: foo]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:int], Const: =, VarDeref: [VarValue: [Const: hehe], Const: haha]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 1.2.3.0/30], EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 5.5.5.5]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 1.2.3.4], EditPropSet: [RelProp: [Const: asn], Const: =, Const: 2]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 1.2.3.4], EditPropSet: [RelProp: [Const: loc], Const: =, Const: us], EditNodeAdd: [FormName: [Const: inet:dns:a], Const: =, List: [Const: vertex.link, Const: 1.2.3.4]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 1.2.3.4]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 192.168.1.0/24]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 4.3.2.1], EditPropSet: [RelProp: [Const: loc], Const: =, Const: zz], EditNodeAdd: [FormName: [Const: inet:dns:a], Const: =, List: [Const: example.com, Const: 4.3.2.1]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 197.231.221.211], EditPropSet: [RelProp: [Const: asn], Const: =, Const: 37560], EditPropSet: [RelProp: [Const: loc], Const: =, Const: lr.lo.voinjama], EditPropSet: [RelProp: [Const: latlong], Const: =, Const: 8.4219,-9.7478], EditPropSet: [RelProp: [Const: dns:rev], Const: =, Const: exit1.ipredator.se], EditTagAdd: [TagName: [Const: cno, Const: anon, Const: tor, Const: exit], Const: =, List: [Const: 2017/12/19, Const: 2019/02/15]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:user], Const: =, Const: visi], EditNodeAdd: [FormName: [Const: inet:user], Const: =, Const: whippit]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:comp], Const: =, List: [Const: 10, Const: haha]], EditTagAdd: [TagName: [Const: foo, Const: bar]], EditTagDel: [TagName: [Const: foo, Const: bar]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:comp], Const: =, List: [Const: 127, Const: newp]], EditNodeAdd: [FormName: [Const: test:comp], Const: =, List: [Const: 127, Const: 127]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:comp], Const: =, List: [Const: 123, Const: test]], EditNodeAdd: [FormName: [Const: test:comp], Const: =, List: [Const: 123, Const: duck]], EditNodeAdd: [FormName: [Const: test:comp], Const: =, List: [Const: 123, Const: mode]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:guid], Const: =, Const: *], EditPropSet: [RelProp: [Const: tick], Const: =, Const: 2015]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:guid], Const: =, Const: *], EditPropSet: [RelProp: [Const: tick], Const: =, Const: 2016]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:guid], Const: =, Const: *], EditPropSet: [RelProp: [Const: tick], Const: =, Const: 2017]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:pivcomp], Const: =, List: [Const: foo, Const: bar]], EditPropSet: [RelProp: [Const: tick], Const: =, Const: 2018]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:pivcomp], Const: =, List: [Const: foo, Const: bar]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:pivcomp], Const: =, List: [Const: hehe, Const: haha]], EditPropSet: [RelProp: [Const: tick], Const: =, Const: 2015], EditTagAdd: [TagName: [Const: foo], Const: =, List: [Const: 2014, Const: 2016]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:pivcomp], Const: =, List: [Const: xxx, Const: yyy]], EditPropSet: [RelProp: [Const: width], Const: =, Const: 42]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo bar], EditPropSet: [RelProp: [Const: tick], Const: =, Const: 2018]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: bar], EditTagAdd: [TagName: [Const: baz]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditTagAdd: [TagName: [VarValue: [Const: tag]]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo], FiltOper: [Const: +, TagCond: [TagMatch: [VarValue: [Const: tag]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditTagAdd: [TagName: [Const: bar]], FiltOper: [Const: +, OrCond: [TagCond: [TagMatch: [Const: baz]], NotCond: [HasRelPropCond: [UnivProp: [Const: .seen]]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditTagAdd: [TagName: [Const: bar]], FiltOper: [Const: +, NotCond: [HasRelPropCond: [UnivProp: [Const: .seen]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditTagAdd: [TagName: [Const: bar]], SubQuery: [Query: [EditTagAdd: [TagName: [Const: baz]], FiltOper: [Const: -, TagCond: [TagMatch: [Const: bar]]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: bar], CmdOper: [Const: sleep, List: [Const: 10]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: bar], CmdOper: [Const: spin, Const: ()]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: bar]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: bar], EditNodeAdd: [FormName: [Const: test:int], Const: =, Const: 42]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: haha], EditTagAdd: [TagName: [Const: bar], Const: =, Const: 2015]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: haha], EditTagAdd: [TagName: [Const: foo]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: hehe], EditTagAdd: [TagName: [Const: foo], Const: =, List: [Const: 2014, Const: 2016]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: hehe]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: oof], EditTagAdd: [TagName: [Const: bar]], SubQuery: [Query: [EditNodeAdd: [FormName: [Const: test:int], Const: =, Const: 0xdeadbeef]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: visi], EditTagAdd: [TagName: [Const: foo, Const: bar]], PivotToTags: [TagMatch: []], isjoin=False, EditTagAdd: [TagName: [Const: baz, Const: faz]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: visi], EditTagAdd: [TagName: [Const: foo, Const: bar]], PivotToTags: [TagMatch: []], isjoin=False]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: visi], EditNodeAdd: [FormName: [Const: test:int], Const: =, Const: 20], EditTagAdd: [TagName: [Const: foo, Const: bar]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: woot], EditTagAdd: [TagName: [Const: foo], Const: =, List: [Const: 2015, Const: 2018]], EditTagAdd: [TagName: [Const: bar]], EditPropSet: [UnivProp: [Const: .seen], Const: =, List: [Const: 2014, Const: 2016]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: woot], EditTagAdd: [TagName: [Const: foo], Const: =, List: [Const: 2015, Const: 2018]], EditPropSet: [UnivProp: [Const: .seen], Const: =, List: [Const: 2014, Const: 2016]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: woot], EditTagAdd: [TagName: [Const: foo], Const: =, List: [Const: 2015, Const: 2018]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: woot], EditPropSet: [UnivProp: [Const: .seen], Const: =, List: [Const: 2014, Const: 2015]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: woot], EditPropSet: [UnivProp: [Const: .seen], Const: =, Const: 20]]',
    'Query: [EditTagDel: [TagName: [Const: foo]]]',
    'Query: [EditNodeAdd: [FormName: [Const: meta:source], Const: =, List: [List: [Const: test:str, Const: foobar], List: [Const: test:str, Const: foo]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: meta:source], Const: =, List: [List: [Const: test:comp, List: [Const: 2048, Const: horton]], List: [Const: test:comp, List: [Const: 4096, Const: whoville]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: meta:source], Const: =, List: [List: [Const: test:comp, List: [Const: 9001, Const: A mean one]], List: [Const: test:comp, List: [Const: 40000, Const: greeneggs]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: meta:source], Const: =, List: [List: [Const: test:int, Const: 16], List: [Const: test:comp, List: [Const: 9999, Const: greenham]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: meta:source], Const: =, List: [List: [Const: test:str, Const: 123], List: [Const: test:int, Const: 123]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:dns:query], Const: =, List: [Const: tcp://1.2.3.4, Const: , Const: 1]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:dns:query], Const: =, List: [Const: tcp://1.2.3.4, Const: foo*.haha.com, Const: 1]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 1.2.3.1-1.2.3.3]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 1.2.3.4], EditPropSet: [RelProp: [Const: asn], Const: =, Const: 10], EditNodeAdd: [FormName: [Const: meta:source], Const: =, List: [Const: abcd, List: [Const: inet:asn, Const: 10]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: meta:source], Const: =, List: [Const: abcd, List: [Const: test:str, Const: pennywise]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: meta:source], Const: =, Const: abcd], EditTagAdd: [TagName: [Const: omit, Const: nopiv]], EditNodeAdd: [FormName: [Const: meta:source], Const: =, List: [Const: abcd, List: [Const: test:pivtarg, Const: foo]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:comp], Const: =, List: [Const: 1234, Const: 5678]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:comp], Const: =, List: [Const: 3, Const: foob]], EditTagAdd: [TagName: [Const: meep, Const: gorp]], EditTagAdd: [TagName: [Const: bleep, Const: zlorp]], EditTagAdd: [TagName: [Const: cond]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:guid], Const: =, Const: *], EditPropSet: [RelProp: [Const: tick], Const: =, Const: 2001]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:guid], Const: =, Const: abcd], EditPropSet: [RelProp: [Const: tick], Const: =, Const: 2015]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:int], Const: =, Const: 1], EditNodeAdd: [FormName: [Const: test:int], Const: =, Const: 2], EditNodeAdd: [FormName: [Const: test:int], Const: =, Const: 3]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:int], Const: =, Const: 10], EditPropSet: [RelProp: [Const: loc], Const: =, Const: us.va]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:int], Const: =, Const: 2], EditPropSet: [RelProp: [Const: loc], Const: =, Const: us.va.sydney]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:int], Const: =, Const: 20]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:int], Const: =, Const: 3], EditPropSet: [RelProp: [Const: loc], Const: =, Const: ]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:int], Const: =, Const: 4], EditPropSet: [RelProp: [Const: loc], Const: =, Const: us.va.fairfax]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:int], Const: =, Const: 9], EditPropSet: [RelProp: [Const: loc], Const: =, Const: us.ओं]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:int], Const: =, Const: 99999]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:pivcomp], Const: =, List: [Const: foo, Const: 123]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: beep], EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: boop]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditPropSet: [RelProp: [Const: tick], Const: =, Const: 201808021201]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: hehe], CmdOper: [Const: iden, List: [Const: abcd]], CmdOper: [Const: count, Const: ()]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: hello]]',
    'Query: [LiftProp: [Const: meta:source], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: node]], Const: range=, List: [List: [Const: test:comp, List: [Const: 1000, Const: green]], List: [Const: test:comp, List: [Const: 3000, Const: ham]]]]]]',
    'Query: [LiftProp: [Const: meta:source]]',
    'Query: [LiftPropBy: [Const: file:bytes:size, Const: =, Const: 4]]',
    'Query: [ForLoop: [Const: fqdn, VarValue: [Const: fqdns], SubQuery: [Query: [EditNodeAdd: [FormName: [Const: inet:fqdn], Const: =, VarValue: [Const: fqdn]]]]]]',
    "Query: [ForLoop: [VarList: ['fqdn', 'ipv4'], VarValue: [Const: dnsa], SubQuery: [Query: [EditNodeAdd: [FormName: [Const: inet:dns:a], Const: =, List: [VarValue: [Const: fqdn], VarValue: [Const: ipv4]]]]]]]",
    "Query: [ForLoop: [VarList: ['fqdn', 'ipv4', 'boom'], VarValue: [Const: dnsa], SubQuery: [Query: [EditNodeAdd: [FormName: [Const: inet:dns:a], Const: =, List: [VarValue: [Const: fqdn], VarValue: [Const: ipv4]]]]]]]",
    'Query: [LiftProp: [Const: geo:place], FiltOper: [Const: +, AbsPropCond: [Const: geo:place:latlong, Const: near=, List: [List: [Const: 34.1, Const: -118.3], Const: 10km]]]]',
    'Query: [LiftProp: [Const: geo:place], FiltOper: [Const: -, RelPropCond: [RelPropValue: [RelProp: [Const: latlong]], Const: near=, List: [List: [Const: 34.1, Const: -118.3], Const: 50m]]]]',
    'Query: [LiftPropBy: [Const: geo:place:latlong, Const: near=, List: [List: [Const: 34.118560, Const: -118.300370], Const: 2600m]]]',
    'Query: [LiftPropBy: [Const: geo:place:latlong, Const: near=, List: [List: [Const: 34.118560, Const: -118.300370], Const: 50m]]]',
    'Query: [LiftPropBy: [Const: geo:place:latlong, Const: near=, List: [List: [Const: 0, Const: 0], Const: 50m]]]',
    'Query: [LiftPropBy: [Const: geo:place:latlong, Const: near=, List: [List: [Const: 34.1, Const: -118.3], Const: 10km]]]',
    'Query: [LiftPropBy: [Const: geo:place, Const: =, VarValue: [Const: place]], PivotInFrom: [Const: meta:source], isjoin=False, PivotIn: [], isjoin=False]',
    'Query: [LiftPropBy: [Const: geo:place, Const: =, VarValue: [Const: place]], PivotInFrom: [Const: meta:source], isjoin=False, PivotInFrom: [Const: ps:person], isjoin=False]',
    'Query: [LiftPropBy: [Const: geo:place, Const: =, Const: abcd], SetVarOper: [Const: latlong, RelPropValue: [Const: latlong]], SetVarOper: [Const: radius, RelPropValue: [Const: radius]], CmdOper: [Const: spin, Const: ()], LiftPropBy: [Const: tel:mob:telem:latlong, Const: near=, List: [VarValue: [Const: latlong], Const: 3km]]]',
    'Query: [LiftPropBy: [Const: meta:note, Const: =, Const: abcd], CmdOper: [Const: noderefs, List: [Const: -d, Const: 2, Const: --join]]]',
    'Query: [CmdOper: [Const: help, Const: ()]]',
    'Query: [CmdOper: [Const: iden, List: [Const: 2cdd997872b10a65407ad5fadfa28e0d]]]',
    'Query: [CmdOper: [Const: iden, List: [Const: deadb33f]]]',
    'Query: [SetVarOper: [Const: foo, Const: 42], CmdOper: [Const: iden, List: [Const: deadb33f]]]',
    'Query: [LiftPropBy: [Const: inet:asn, Const: =, Const: 10], CmdOper: [Const: noderefs, List: [Const: -of, Const: inet:ipv4, Const: --join, Const: -d, Const: 3]]]',
    'Query: [LiftProp: [Const: inet:dns:a], FiltOper: [Const: +, SubqCond: [Query: [PropPivot: [RelPropValue: [RelProp: [Const: ipv4]], Const: inet:ipv4], isjoin=False, FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: loc]], Const: =, Const: us]]]]]]',
    'Query: [LiftProp: [Const: inet:dns:a], FiltOper: [Const: +, SubqCond: [Query: [PropPivot: [RelPropValue: [RelProp: [Const: ipv4]], Const: inet:ipv4], isjoin=False, FiltOper: [Const: -, RelPropCond: [RelPropValue: [RelProp: [Const: loc]], Const: =, Const: us]]]]]]',
    'Query: [LiftProp: [Const: inet:dns:a], FiltOper: [Const: -, SubqCond: [Query: [PropPivot: [RelPropValue: [RelProp: [Const: ipv4]], Const: inet:ipv4], isjoin=False, FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: loc]], Const: =, Const: us]]]]]]',
    'Query: [LiftProp: [Const: inet:dns:a], FiltOper: [Const: -, SubqCond: [Query: [PropPivot: [RelPropValue: [RelProp: [Const: ipv4]], Const: inet:ipv4], isjoin=False, FiltOper: [Const: -, RelPropCond: [RelPropValue: [RelProp: [Const: loc]], Const: =, Const: us]]]]]]',
    'Query: [LiftProp: [Const: inet:dns:a], PropPivotOut: [RelProp: [Const: ipv4]], isjoin=False]',
    'Query: [LiftPropBy: [Const: inet:dns:a, Const: =, List: [Const: woot.com, Const: 12.34.56.78]], EditPropSet: [UnivProp: [Const: .seen], Const: =, List: [Const: 201708010123, Const: 201708100456]]]',
    'Query: [LiftPropBy: [Const: inet:dns:a, Const: =, List: [Const: woot.com, Const: 12.34.56.78]], EditPropSet: [UnivProp: [Const: .seen], Const: =, List: [Const: 201708010123, Const: ?]]]',
    'Query: [LiftProp: [Const: inet:dns:a]]',
    'Query: [LiftPropBy: [Const: inet:dns:a, Const: =, List: [Const: woot.com, Const: 1.2.3.4]], SetVarOper: [Const: hehe, RelPropValue: [Const: fqdn]], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: fqdn]], Const: =, VarValue: [Const: hehe]]]]',
    'Query: [LiftPropBy: [Const: inet:dns:a, Const: =, List: [Const: woot.com, Const: 1.2.3.4]], SetVarOper: [Const: hehe, RelPropValue: [Const: fqdn]], FiltOper: [Const: -, RelPropCond: [RelPropValue: [RelProp: [Const: fqdn]], Const: =, VarValue: [Const: hehe]]]]',
    'Query: [LiftPropBy: [Const: inet:dns:a, Const: =, List: [Const: woot.com, Const: 1.2.3.4]], SetVarOper: [Const: hehe, RelPropValue: [Const: fqdn]], LiftPropBy: [Const: inet:fqdn, Const: =, VarValue: [Const: hehe]]]',
    'Query: [LiftPropBy: [Const: inet:dns:a, Const: =, List: [Const: woot.com, Const: 1.2.3.4]], SetVarOper: [Const: newp, UnivPropValue: [UnivProp: [Const: .seen]]]]',
    'Query: [LiftPropBy: [Const: inet:dns:a, Const: =, List: [Const: woot.com, Const: 1.2.3.4]], SetVarOper: [Const: seen, UnivPropValue: [UnivProp: [Const: .seen]]], PropPivot: [RelPropValue: [RelProp: [Const: fqdn]], Const: inet:fqdn], isjoin=False, EditPropSet: [UnivProp: [Const: .seen], Const: =, VarValue: [Const: seen]]]',
    'Query: [LiftPropBy: [Const: inet:dns:a, Const: =, List: [Const: woot.com, Const: 1.2.3.4]], EditPropSet: [UnivProp: [Const: .seen], Const: =, List: [Const: 2015, Const: 2018]]]',
    'Query: [LiftPropBy: [Const: inet:dns:query, Const: =, List: [Const: tcp://1.2.3.4, Const: , Const: 1]], PropPivot: [RelPropValue: [RelProp: [Const: name]], Const: inet:fqdn], isjoin=False]',
    'Query: [LiftPropBy: [Const: inet:dns:query, Const: =, List: [Const: tcp://1.2.3.4, Const: foo*.haha.com, Const: 1]], PropPivot: [RelPropValue: [RelProp: [Const: name]], Const: inet:fqdn], isjoin=False]',
    'Query: [LiftProp: [Const: inet:fqdn], FiltOper: [Const: +, TagCond: [TagMatch: [Const: bad]]], SetVarOper: [Const: fqdnbad, TagValue: [TagName: [Const: bad]]], FormPivot: [Const: inet:dns:a:fqdn], isjoin=False, FiltOper: [Const: +, RelPropCond: [RelPropValue: [UnivProp: [Const: .seen]], Const: @=, VarValue: [Const: fqdnbad]]]]',
    'Query: [LiftPropBy: [Const: inet:fqdn, Const: =, Const: woot.com], FormPivot: [Const: inet:dns:a], isjoin=False, FormPivot: [Const: inet:ipv4], isjoin=False]',
    'Query: [LiftPropBy: [Const: inet:fqdn, Const: =, Const: woot.com], FormPivot: [Const: inet:dns:a], isjoin=False]',
    'Query: [LiftPropBy: [Const: inet:fqdn, Const: =, Const: woot.com], CmdOper: [Const: delnode, Const: ()]]',
    'Query: [LiftProp: [Const: inet:fqdn], CmdOper: [Const: graph, List: [Const: --filter, ArgvQuery: [Query: [FiltOper: [Const: -, TagCond: [TagMatch: [Const: nope]]]]]]]]',
    'Query: [LiftPropBy: [Const: inet:fqdn, Const: =, Const: woot.com]]',
    'Query: [LiftProp: [Const: inet:ipv4], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: asn::name]], Const: =, Const: visi]]]',
    'Query: [LiftProp: [Const: inet:ipv4], FiltOper: [Const: +, AbsPropCond: [Const: inet:ipv4, Const: =, Const: 1.2.3.0/30]]]',
    'Query: [LiftProp: [Const: inet:ipv4], FiltOper: [Const: +, AbsPropCond: [Const: inet:ipv4, Const: =, Const: 1.2.3.1-1.2.3.3]]]',
    'Query: [LiftProp: [Const: inet:ipv4], FiltOper: [Const: +, AbsPropCond: [Const: inet:ipv4, Const: =, Const: 10.2.1.4/32]]]',
    'Query: [LiftProp: [Const: inet:ipv4], FormPivot: [Const: test:str], isjoin=False]',
    'Query: [LiftProp: [Const: inet:ipv4], CmdOper: [Const: reindex, List: [Const: --subs]]]',
    'Query: [LiftPropBy: [Const: inet:ipv4:loc, Const: =, Const: us]]',
    'Query: [LiftPropBy: [Const: inet:ipv4:loc, Const: =, Const: zz]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.1-1.2.3.3]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 192.168.1.0/24]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.4], FiltOper: [Const: +, HasRelPropCond: [RelProp: [Const: asn]]]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.4], FiltOper: [Const: +, SubqCond: [Query: [FormPivot: [Const: inet:dns:a], isjoin=False], Const: <, Const: 2]]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.4], FiltOper: [Const: +, SubqCond: [Query: [FormPivot: [Const: inet:dns:a], isjoin=False], Const: <=, Const: 1]]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.4], FiltOper: [Const: +, SubqCond: [Query: [FormPivot: [Const: inet:dns:a], isjoin=False], Const: !=, Const: 2]]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.4], CmdOper: [Const: limit, List: [Const: 20]]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 12.34.56.78], EditPropSet: [RelProp: [Const: loc], Const: =, Const: us.oh.wilmington]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 12.34.56.78], LiftPropBy: [Const: inet:fqdn, Const: =, Const: woot.com], EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 1.2.3.4], EditPropSet: [RelProp: [Const: asn], Const: =, Const: 10101], EditNodeAdd: [FormName: [Const: inet:fqdn], Const: =, Const: woowoo.com], EditTagAdd: [TagName: [Const: my, Const: tag]]]',
    'Query: [LiftProp: [Const: inet:user], CmdOper: [Const: limit, List: [Const: --woot]]]',
    'Query: [LiftProp: [Const: inet:user], CmdOper: [Const: limit, List: [Const: 1]]]',
    'Query: [LiftProp: [Const: inet:user], CmdOper: [Const: limit, List: [Const: 10]], FiltOper: [Const: +, AbsPropCond: [Const: inet:user, Const: =, Const: visi]]]',
    'Query: [LiftProp: [Const: inet:user], CmdOper: [Const: limit, List: [Const: 10]], EditTagAdd: [TagName: [Const: foo, Const: bar]]]',
    'Query: [LiftPropBy: [Const: media:news, Const: =, Const: 00a1f0d928e25729b9e86e2d08c127ce], EditPropSet: [RelProp: [Const: summary], Const: =, Const: ]]',
    'Query: [LiftPropBy: [Const: meta:source:meta:source, Const: =, VarValue: [Const: sorc]], PivotOut: [], isjoin=False]',
    'Query: [LiftPropBy: [Const: meta:source:meta:source, Const: =, VarValue: [Const: sorc]], PropPivotOut: [RelProp: [Const: node]], isjoin=False]',
    'Query: [LiftPropBy: [Const: meta:source, Const: =, Const: 8f1401de15918358d5247e21ca29a814]]',
    'Query: [CmdOper: [Const: movetag, List: [Const: a.b, Const: a.m]]]',
    'Query: [CmdOper: [Const: movetag, List: [Const: hehe, Const: woot]]]',
    'Query: [LiftPropBy: [Const: ps:person, Const: =, VarValue: [Const: pers]], FormPivot: [Const: meta:source], isjoin=False, PivotOut: [], isjoin=False]',
    'Query: [LiftPropBy: [Const: ps:person, Const: =, VarValue: [Const: pers]], FormPivot: [Const: meta:source], isjoin=False, FormPivot: [Const: geo:place], isjoin=False]',
    'Query: [LiftPropBy: [Const: ps:person, Const: =, VarValue: [Const: pers]], FormPivot: [Const: meta:source], isjoin=False, FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: time]], Const: @=, List: [Const: 2014, Const: 2017]]], FormPivot: [Const: geo:place], isjoin=False]',
    'Query: [LiftPropBy: [Const: ps:person, Const: =, VarValue: [Const: pers]], FormPivot: [Const: meta:source], isjoin=False, PivotOut: [], isjoin=False]',
    'Query: [LiftPropBy: [Const: ps:person, Const: =, VarValue: [Const: pers]], FormPivot: [Const: meta:source], isjoin=False, PropPivotOut: [RelProp: [Const: node]], isjoin=False]',
    'Query: [CmdOper: [Const: reindex, List: [Const: --form-counts]]]',
    'Query: [CmdOper: [Const: sudo, Const: ()], EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 1.2.3.4]]',
    'Query: [CmdOper: [Const: sudo, Const: ()], EditNodeAdd: [FormName: [Const: test:cycle0], Const: =, Const: foo], EditPropSet: [RelProp: [Const: test:cycle1], Const: =, Const: bar]]',
    'Query: [CmdOper: [Const: sudo, Const: ()], EditNodeAdd: [FormName: [Const: test:guid], Const: =, Const: *]]',
    'Query: [CmdOper: [Const: sudo, Const: ()], EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditTagAdd: [TagName: [Const: lol]]]',
    'Query: [CmdOper: [Const: sudo, Const: ()], EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo]]',
    'Query: [CmdOper: [Const: sudo, Const: ()], EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: 123], EditPropSet: [RelProp: [Const: tick], Const: =, Const: 2018]]',
    'Query: [CmdOper: [Const: sudo, Const: ()], LiftPropBy: [Const: test:int, Const: =, Const: 6], CmdOper: [Const: delnode, Const: ()]]',
    'Query: [LiftPropBy: [Const: syn:tag, Const: =, Const: a.b], FiltOper: [Const: +, TagCond: [TagMatch: [Const: foo]]]]',
    'Query: [LiftPropBy: [Const: syn:tag, Const: =, Const: aaa.barbarella.ddd]]',
    'Query: [LiftPropBy: [Const: syn:tag, Const: =, Const: baz.faz], EditTagAdd: [TagName: [Const: foo, Const: bar]]]',
    'Query: [LiftPropBy: [Const: syn:tag, Const: =, Const: foo.bar], PivotOut: [], isjoin=False]',
    'Query: [LiftPropBy: [Const: syn:tag, Const: =, Const: foo.bar], FormPivot: [Const: test:str], isjoin=False]',
    'Query: [LiftPropBy: [Const: syn:tag, Const: =, Const: foo.bar], FormPivot: [Const: test:str:tick], isjoin=False]',
    'Query: [LiftProp: [Const: test:comp], FiltOper: [Const: +, AndCond: [RelPropCond: [RelPropValue: [RelProp: [Const: hehe]], Const: <, Const: 2], RelPropCond: [RelPropValue: [RelProp: [Const: haha]], Const: =, Const: test]]]]',
    'Query: [LiftProp: [Const: test:comp], FiltOper: [Const: +, OrCond: [RelPropCond: [RelPropValue: [RelProp: [Const: hehe]], Const: <, Const: 2], TagCond: [TagMatch: [Const: meep, Const: gorp]]]]]',
    'Query: [LiftProp: [Const: test:comp], FiltOper: [Const: +, OrCond: [RelPropCond: [RelPropValue: [RelProp: [Const: hehe]], Const: <, Const: 2], RelPropCond: [RelPropValue: [RelProp: [Const: haha]], Const: =, Const: test]]]]',
    'Query: [LiftProp: [Const: test:comp], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: haha]], Const: range=, List: [Const: grinch, Const: meanone]]]]',
    'Query: [LiftProp: [Const: test:comp], FiltOper: [Const: +, AbsPropCond: [Const: test:comp, Const: range=, List: [List: [Const: 1024, Const: grinch], List: [Const: 4096, Const: zemeanone]]]]]',
    'Query: [LiftProp: [Const: test:comp], PivotOut: [], isjoin=False, CmdOper: [Const: uniq, Const: ()], CmdOper: [Const: count, Const: ()]]',
    'Query: [LiftProp: [Const: test:comp], PivotOut: [], isjoin=False]',
    'Query: [LiftProp: [Const: test:comp], FormPivot: [Const: test:int], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:comp:haha, Const: ~=, Const: ^lulz]]',
    'Query: [LiftPropBy: [Const: test:comp:haha, Const: ~=, Const: ^zerg]]',
    'Query: [LiftFormTag: [Const: test:comp, TagName: [Const: bar]], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: hehe]], Const: =, Const: 1010]], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: haha]], Const: =, Const: test10]], FiltOper: [Const: +, TagCond: [TagMatch: [Const: bar]]]]',
    'Query: [LiftProp: [Const: test:guid], FiltOper: [Const: +, AbsPropCond: [Const: test:guid, Const: range=, List: [Const: abcd, Const: dcbe]]]]',
    'Query: [LiftProp: [Const: test:guid], CmdOper: [Const: max, List: [Const: tick]]]',
    'Query: [LiftProp: [Const: test:guid], CmdOper: [Const: min, List: [Const: tick]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: loc]], Const: =, Const: ]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: loc]], Const: =, Const: us.va. syria]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: loc]], Const: =, Const: u]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: loc]], Const: =, Const: us]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: loc]], Const: =, Const: us.v]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: loc]], Const: =, Const: us.va.sydney]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: loc]], Const: ^=, Const: ]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: loc]], Const: ^=, Const: 23]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: loc]], Const: ^=, Const: u]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: loc]], Const: ^=, Const: us]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: loc]], Const: ^=, Const: us.]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: loc]], Const: ^=, Const: us.va.]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: loc]], Const: ^=, Const: us.va.fairfax.reston]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, AbsPropCond: [Const: test:int, Const: <, Const: 30]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, AbsPropCond: [Const: test:int, Const: <=, Const: 30]]]',
    'Query: [LiftPropBy: [Const: test:int, Const: <=, Const: 20]]',
    'Query: [LiftProp: [Const: test:int], CmdOper: [Const: noderefs, Const: ()], FiltOper: [Const: +, AbsPropCond: [Const: test:comp, Const: range=, List: [List: [Const: 1000, Const: grinch], List: [Const: 4000, Const: whoville]]]]]',
    'Query: [LiftPropBy: [Const: test:int:loc, Const: =, Const: ]]',
    'Query: [LiftPropBy: [Const: test:int:loc, Const: =, Const: u]]',
    'Query: [LiftPropBy: [Const: test:int:loc, Const: =, Const: us]]',
    'Query: [LiftPropBy: [Const: test:int:loc, Const: ^=, Const: ]]',
    'Query: [LiftPropBy: [Const: test:int:loc, Const: ^=, Const: 23]]',
    'Query: [LiftPropBy: [Const: test:int:loc, Const: ^=, Const: u]]',
    'Query: [LiftPropBy: [Const: test:int:loc, Const: ^=, Const: us]]',
    'Query: [LiftPropBy: [Const: test:int:loc, Const: ^=, Const: us.]]',
    'Query: [LiftPropBy: [Const: test:int:loc, Const: ^=, Const: us.va.fairfax.reston]]',
    'Query: [LiftPropBy: [Const: test:int, Const: <, Const: 30]]',
    'Query: [LiftPropBy: [Const: test:int, Const: <=, Const: 30]]',
    'Query: [LiftPropBy: [Const: test:int, Const: =, Const: 123], CmdOper: [Const: noderefs, List: [Const: -te]]]',
    'Query: [LiftPropBy: [Const: test:int, Const: =, Const: 123], CmdOper: [Const: noderefs, Const: ()]]',
    'Query: [LiftPropBy: [Const: test:int, Const: =, Const: 1234], EditNodeAdd: [FormName: [Const: test:str], Const: =, FuncCall: [VarDeref: [VarValue: [Const: node], Const: form], CallArgs: [], CallKwargs: []]], FiltOper: [Const: -, HasAbsPropCond: [Const: test:int]]]',
    'Query: [LiftPropBy: [Const: test:int, Const: =, Const: 1234], EditNodeAdd: [FormName: [Const: test:str], Const: =, FuncCall: [VarDeref: [VarValue: [Const: node], Const: value], CallArgs: [], CallKwargs: []]], FiltOper: [Const: -, HasAbsPropCond: [Const: test:int]]]',
    'Query: [LiftPropBy: [Const: test:int, Const: =, Const: 3735928559]]',
    'Query: [LiftPropBy: [Const: test:int, Const: =, Const: 8675309]]',
    'Query: [LiftPropBy: [Const: test:int, Const: >, Const: 30]]',
    'Query: [LiftPropBy: [Const: test:int, Const: >=, Const: 20]]',
    'Query: [LiftProp: [Const: test:pivcomp], FormPivot: [Const: test:int], isjoin=False]',
    'Query: [LiftProp: [Const: test:pivcomp], CmdOper: [Const: noderefs, List: [Const: --join, Const: --degrees, Const: 2]]]',
    'Query: [LiftProp: [Const: test:pivcomp], CmdOper: [Const: noderefs, List: [Const: --join, Const: -d, Const: 3]]]',
    'Query: [LiftProp: [Const: test:pivcomp], CmdOper: [Const: noderefs, List: [Const: --join]]]',
    'Query: [LiftProp: [Const: test:pivcomp], CmdOper: [Const: noderefs, List: [Const: -j, Const: --degrees, Const: 2]]]',
    'Query: [LiftProp: [Const: test:pivcomp], CmdOper: [Const: noderefs, Const: ()]]',
    'Query: [LiftPropBy: [Const: test:pivcomp:tick, Const: =, VarValue: [Const: foo]]]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, VarValue: [Const: foo]]]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], FiltOper: [Const: +, SubqCond: [Query: [PropPivot: [RelPropValue: [RelProp: [Const: lulz]], Const: test:str], isjoin=False, FiltOper: [Const: +, TagCond: [TagMatch: [Const: baz]]]]]], FiltOper: [Const: +, HasAbsPropCond: [Const: test:pivcomp]]]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], PivotOut: [], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], FormPivot: [Const: test:pivtarg], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], PivotOut: [], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], FormPivot: [Const: test:pivtarg], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], FiltOper: [Const: -, SubqCond: [Query: [PropPivot: [RelPropValue: [RelProp: [Const: lulz]], Const: test:str], isjoin=False, FiltOper: [Const: +, TagCond: [TagMatch: [Const: baz]]]]]]]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], PropPivot: [RelPropValue: [RelProp: [Const: lulz]], Const: test:str], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], PropPivot: [RelPropValue: [RelProp: [Const: lulz]], Const: test:str], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], PropPivot: [RelPropValue: [RelProp: [Const: targ]], Const: test:pivtarg], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: hehe, Const: haha]], SetVarOper: [Const: ticktock, TagValue: [TagName: [Const: foo]]], FormPivot: [Const: test:pivtarg], isjoin=False, FiltOper: [Const: +, RelPropCond: [RelPropValue: [UnivProp: [Const: .seen]], Const: @=, VarValue: [Const: ticktock]]]]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: hehe, Const: haha]]]',
    'Query: [LiftPropBy: [Const: test:pivtarg, Const: =, Const: hehe], EditPropSet: [UnivProp: [Const: .seen], Const: =, Const: 2015]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, TagCond: [TagMatch: [Const: *]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, TagCond: [TagMatch: [Const: **, Const: bar, Const: baz]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, TagCond: [TagMatch: [Const: **, Const: baz]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, TagCond: [TagMatch: [Const: *, Const: bad]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, TagCond: [TagMatch: [Const: foo, Const: **, Const: baz]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, TagCond: [TagMatch: [Const: foo, Const: *, Const: baz]]]]',
    'Query: [LiftTag: [TagName: [Const: foo], Const: @=, List: [Const: 2013, Const: 2015]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, TagValuCond: [TagMatch: [Const: foo], Const: @=, List: [Const: 2014, Const: 20141231]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, TagValuCond: [TagMatch: [Const: foo], Const: @=, List: [Const: 2015, Const: 2018]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, TagValuCond: [TagMatch: [Const: foo], Const: @=, Const: 2016]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: bar]], Const: range=, List: [List: [Const: test:str, Const: c], List: [Const: test:str, Const: q]]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: tick]], Const: range=, List: [Const: 19701125, Const: 20151212]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: tick]], Const: =, List: [VarValue: [Const: test], Const: +- 2day]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: tick]], Const: =, List: [Const: 2015, Const: +1 day]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: tick]], Const: =, List: [Const: 20150102, Const: -3 day]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: tick]], Const: =, List: [Const: 20150201, Const: +1 day]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: tick]], Const: =, Const: 2015]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: tick]], Const: @=, Const: -1 day]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: tick]], Const: @=, List: [Const: now+2days, Const: -3 day]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: tick]], Const: @=, List: [Const: now-1day, Const: ?]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: tick]], Const: @=, Const: 2015]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: tick]], Const: @=, List: [Const: 2015, Const: +1 day]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: tick]], Const: @=, List: [Const: 20150102+1day, Const: -4 day]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: tick]], Const: @=, List: [Const: 20150102, Const: -4 day]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: tick]], Const: @=, List: [Const: now, Const: -1 day]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, AbsPropCond: [Const: test:str:tick, Const: <, Const: 201808021202]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, AbsPropCond: [Const: test:str:tick, Const: <=, Const: 201808021202]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, AbsPropCond: [Const: test:str:tick, Const: >, Const: 201808021202]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, AbsPropCond: [Const: test:str:tick, Const: >=, Const: 201808021202]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: -, TagCond: [TagMatch: [Const: *]]]]',
    'Query: [LiftProp: [Const: test:str], EditTagAdd: [TagName: [Const: foo, Const: bar], Const: =, List: [Const: 2000, Const: 2002]]]',
    'Query: [LiftProp: [Const: test:str], EditTagAdd: [TagName: [Const: foo, Const: bar], Const: =, List: [Const: 2000, Const: 20020601]]]',
    'Query: [LiftProp: [Const: test:str], EditTagAdd: [TagName: [Const: foo, Const: bar]]]',
    'Query: [LiftProp: [Const: test:str], EditTagDel: [TagName: [Const: foo]]]',
    'Query: [LiftProp: [Const: test:str], EditPropDel: [RelProp: [Const: tick]]]',
    'Query: [LiftProp: [Const: test:str], CmdOper: [Const: delnode, List: [Const: --force]]]',
    'Query: [LiftProp: [Const: test:str], CmdOper: [Const: noderefs, List: [Const: -d, Const: 3, Const: --unique]]]',
    'Query: [LiftProp: [Const: test:str], CmdOper: [Const: noderefs, List: [Const: -d, Const: 3]]]',
    'Query: [LiftFormTag: [Const: test:str, TagName: [Const: foo]]]',
    'Query: [LiftFormTag: [Const: test:str, TagName: [Const: foo, Const: bar]]]',
    'Query: [LiftFormTag: [Const: test:str, TagName: [Const: foo], Const: @=, List: [Const: 2012, Const: 2022]]]',
    'Query: [LiftFormTag: [Const: test:str, TagName: [Const: foo], Const: @=, Const: 2016]]',
    'Query: [LiftProp: [Const: test:str]]',
    'Query: [LiftPropBy: [Const: test:str:tick, Const: <, Const: 201808021202]]',
    'Query: [LiftPropBy: [Const: test:str:tick, Const: <=, Const: 201808021202]]',
    'Query: [LiftPropBy: [Const: test:str:tick, Const: =, List: [Const: 20131231, Const: +2 days]]]',
    'Query: [LiftPropBy: [Const: test:str:tick, Const: =, Const: 2015]]',
    'Query: [LiftPropBy: [Const: test:str:tick, Const: >, Const: 201808021202]]',
    'Query: [LiftPropBy: [Const: test:str:tick, Const: >=, Const: 201808021202]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo bar], FiltOper: [Const: +, HasAbsPropCond: [Const: test:str]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo bar], FiltOper: [Const: -, HasAbsPropCond: [Const: test:str:tick]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo bar], EditPropDel: [RelProp: [Const: tick]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, VarValue: [Const: foo]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: 123], EditPropSet: [RelProp: [Const: baz], Const: =, Const: test:guid:tick=2015]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: 123], CmdOper: [Const: noderefs, List: [Const: --traverse-edge]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: 123], CmdOper: [Const: noderefs, Const: ()]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: 1234], LiftPropBy: [Const: test:str, Const: =, Const: duck], LiftPropBy: [Const: test:str, Const: =, Const: knight]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: a], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: [Const: tick]], Const: range=, List: [Const: 20000101, Const: 20101201]]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: bar], FormPivot: [Const: test:pivcomp:lulz], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: bar], FormPivot: [Const: test:pivcomp:lulz], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: bar], PivotIn: [], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: bar], PivotIn: [], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: bar], LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], EditTagAdd: [TagName: [Const: test, Const: bar]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo], FiltOper: [Const: +, TagValuCond: [TagMatch: [Const: lol], Const: @=, Const: 2016]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo], PivotInFrom: [Const: meta:source], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo], PivotInFrom: [Const: meta:source], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo], CmdOper: [Const: delnode, Const: ()]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foobar], FormPivot: [Const: meta:source], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foobar], FormPivot: [Const: meta:source], isjoin=False, PivotInFrom: [Const: test:str], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foobar], FormPivot: [Const: meta:source], isjoin=False, PivotInFrom: [Const: test:str], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: hello], EditPropSet: [RelProp: [Const: tick], Const: =, Const: 2001]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: hello], EditPropSet: [RelProp: [Const: tick], Const: =, Const: 2002]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: pennywise], CmdOper: [Const: noderefs, List: [Const: --join, Const: -d, Const: 9, Const: --traverse-edge]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: pennywise], CmdOper: [Const: noderefs, List: [Const: -d, Const: 3, Const: --omit-traversal-tag, Const: omit.nopiv, Const: --omit-traversal-tag, Const: test]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: visi], PivotToTags: [TagMatch: [Const: *]], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: visi], PivotToTags: [TagMatch: [Const: foo, Const: *]], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: woot], SetVarOper: [Const: foo, TagValue: [TagName: [Const: foo]]], FiltOper: [Const: +, RelPropCond: [RelPropValue: [UnivProp: [Const: .seen]], Const: @=, VarValue: [Const: foo]]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: woot], FiltOper: [Const: +, RelPropCond: [RelPropValue: [UnivProp: [Const: .seen]], Const: @=, TagValue: [TagName: [Const: bar]]]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: woot], FiltOper: [Const: +, RelPropCond: [RelPropValue: [UnivProp: [Const: .seen]], Const: @=, List: [Const: 2012, Const: 2015]]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: woot], FiltOper: [Const: +, RelPropCond: [RelPropValue: [UnivProp: [Const: .seen]], Const: @=, Const: 2012]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: ~=, Const: zip]]',
    "Query: [ForLoop: [Const: foo, VarValue: [Const: foos], SubQuery: [Query: [VarListSetOper: [VarList: ['fqdn', 'ipv4'], FuncCall: [VarDeref: [VarValue: [Const: foo], Const: split], CallArgs: [Const: |], CallKwargs: []]], EditNodeAdd: [FormName: [Const: inet:dns:a], Const: =, List: [VarValue: [Const: fqdn], VarValue: [Const: ipv4]]]]]]]",
    'Query: [LiftProp: [Const: test:int]]',
    'Query: [LiftProp: [Const: test:int]]',
    'Query: [LiftProp: [Const: test:int]]',
    'Query: [LiftProp: [Const: inet:fqdn], CmdOper: [Const: graph, List: [Const: --degrees, Const: 2, Const: --filter, ArgvQuery: [Query: [FiltOper: [Const: -, TagCond: [TagMatch: [Const: nope]]]]], Const: --pivot, ArgvQuery: [Query: [PivotInFrom: [Const: meta:source], isjoin=False, PivotInFrom: [Const: meta:source], isjoin=False]], Const: --form-pivot, Const: inet:fqdn, ArgvQuery: [Query: [PivotIn: [], isjoin=False, CmdOper: [Const: limit, List: [Const: 20]]]], Const: --form-pivot, Const: inet:fqdn, ArgvQuery: [Query: [PivotOut: [], isjoin=False, CmdOper: [Const: limit, List: [Const: 20]]]], Const: --form-filter, Const: inet:fqdn, ArgvQuery: [Query: [FiltOper: [Const: -, AbsPropCond: [Const: inet:fqdn:issuffix, Const: =, Const: 1]]]], Const: --form-pivot, Const: syn:tag, ArgvQuery: [Query: [PivotOut: [], isjoin=False]], Const: --form-pivot, Const: *, ArgvQuery: [Query: [PivotToTags: [TagMatch: []], isjoin=False]]]]]',
    "Query: [ForLoop: [Const: foo, VarValue: [Const: foos], SubQuery: [Query: [VarListSetOper: [VarList: ['fqdn', 'ipv4'], FuncCall: [VarDeref: [VarValue: [Const: foo], Const: split], CallArgs: [Const: |], CallKwargs: []]], EditNodeAdd: [FormName: [Const: inet:dns:a], Const: =, List: [VarValue: [Const: fqdn], VarValue: [Const: ipv4]]]]]]]",
    'Query: [ForLoop: [Const: tag, FuncCall: [VarDeref: [VarValue: [Const: node], Const: tags], CallArgs: [], CallKwargs: []], SubQuery: [Query: [FormPivot: [Const: test:int], isjoin=False, EditTagAdd: [TagName: [VarValue: [Const: tag]]]]]]]',
    'Query: [ForLoop: [Const: tag, FuncCall: [VarDeref: [VarValue: [Const: node], Const: tags], CallArgs: [Const: fo*], CallKwargs: []], SubQuery: [Query: [FormPivot: [Const: test:int], isjoin=False, EditTagDel: [TagName: [VarValue: [Const: tag]]]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:email:message], Const: =, Const: *], EditPropSet: [RelProp: [Const: to], Const: =, Const: woot@woot.com], EditPropSet: [RelProp: [Const: from], Const: =, Const: visi@vertex.link], EditPropSet: [RelProp: [Const: replyto], Const: =, Const: root@root.com], EditPropSet: [RelProp: [Const: subject], Const: =, Const: hi there], EditPropSet: [RelProp: [Const: date], Const: =, Const: 2015], EditPropSet: [RelProp: [Const: body], Const: =, Const: there are mad sploitz here!], EditPropSet: [RelProp: [Const: bytes], Const: =, Const: *], SubQuery: [Query: [EditNodeAdd: [FormName: [Const: inet:email:message:link], Const: =, List: [VarValue: [Const: node], Const: https://www.vertex.link]]]], SubQuery: [Query: [EditNodeAdd: [FormName: [Const: inet:email:message:attachment], Const: =, List: [VarValue: [Const: node], Const: *]], FiltOper: [Const: -, HasAbsPropCond: [Const: inet:email:message]], EditPropSet: [RelProp: [Const: name], Const: =, Const: sploit.exe]]], SubQuery: [Query: [EditNodeAdd: [FormName: [Const: meta:source], Const: =, List: [VarValue: [Const: node], List: [Const: inet:email:header, List: [Const: to, Const: Visi Kensho <visi@vertex.link>]]]]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [Const: 1, Const: /, Const: 3]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [Const: 1, Const: *, Const: 3]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [ExprNode: [Const: 1, Const: *, Const: 3], Const: +, Const: 2]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [Const: 1, Const: -, ExprNode: [Const: 3.2, Const: /, Const: -3.2]]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [Const: 1, Const: +, ExprNode: [Const: 3, Const: /, Const: 2]]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [DollarExpr: [ExprNode: [Const: 1, Const: +, Const: 3]], Const: /, Const: 2]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [Const: 2, Const: **, Const: 4]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [Const: 2, Const: %, Const: 4]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [Const: 5, Const: +, ExprNode: [Const: 100, Const: %, Const: 3]]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [Const: 5, Const: -, ExprNode: [Const: 100, Const: %, Const: 3]]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [ExprNode: [Const: 5, Const: *, Const: 100], Const: %, Const: 3]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [ExprNode: [Const: 5, Const: /, Const: 100], Const: %, Const: 3]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [Const: 5, Const: +, ExprNode: [Const: 100, Const: %, Const: 3]]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [Const: 5, Const: -, ExprNode: [Const: 100, Const: %, Const: 3]]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [ExprNode: [Const: 5, Const: *, Const: 100], Const: %, Const: 3]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [ExprNode: [Const: 5, Const: /, Const: 100], Const: %, Const: 3]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [Const: 5, Const: +, ExprNode: [Const: 256, Const: %, Const: 3]]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [Const: 5, Const: -, ExprNode: [Const: 256, Const: %, Const: 3]]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [ExprNode: [Const: 5, Const: *, Const: 256], Const: %, Const: 3]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [ExprNode: [Const: 5, Const: /, Const: 256], Const: %, Const: 3]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [Const: 5, Const: +, ExprNode: [Const: 64, Const: %, Const: 3]]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [Const: 5, Const: -, ExprNode: [Const: 64, Const: %, Const: 3]]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [ExprNode: [Const: 5, Const: *, Const: 64], Const: %, Const: 3]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [ExprNode: [Const: 5, Const: /, Const: 64], Const: %, Const: 3]]]]',
    'Query: [SetVarOper: [Const: foo, Const: 42], SetVarOper: [Const: foo2, Const: 43], SetVarOper: [Const: x, DollarExpr: [ExprNode: [VarValue: [Const: foo], Const: *, VarValue: [Const: foo2]]]]]',
    'Query: [SetVarOper: [Const: yep, DollarExpr: [ExprNode: [Const: 42, Const: <, Const: 43]]]]',
    'Query: [SetVarOper: [Const: yep, DollarExpr: [ExprNode: [Const: 42, Const: >, Const: 43]]]]',
    'Query: [SetVarOper: [Const: yep, DollarExpr: [ExprNode: [Const: 42, Const: >=, Const: 43]]]]',
    'Query: [SetVarOper: [Const: yep, DollarExpr: [ExprNode: [ExprNode: [Const: 42, Const: +, Const: 4], Const: <=, ExprNode: [Const: 43, Const: *, Const: 43]]]]]',
    'Query: [SetVarOper: [Const: foo, Const: 4.3], SetVarOper: [Const: bar, Const: 4.2], SetVarOper: [Const: baz, DollarExpr: [ExprNode: [VarValue: [Const: foo], Const: +, VarValue: [Const: bar]]]]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1], SetVarOper: [Const: foo, UnivPropValue: [UnivProp: [Const: .created]]], SetVarOper: [Const: bar, DollarExpr: [ExprNode: [VarValue: [Const: foo], Const: +, Const: 1]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [FuncCall: [VarDeref: [VarDeref: [VarValue: [Const: lib], Const: time], Const: offset], CallArgs: [Const: 2 days], CallKwargs: []]]]]',
    'Query: [SetVarOper: [Const: foo, Const: 1], SetVarOper: [Const: bar, Const: 2], LiftPropBy: [Const: inet:ipv4, Const: =, DollarExpr: [ExprNode: [VarValue: [Const: foo], Const: +, VarValue: [Const: bar]]]]]',
    'Query: []',
    'Query: [CmdOper: [Const: hehe.haha, List: [Const: --size, Const: 10, Const: --query, Const: foo_bar.stuff:baz]]]',
    'Query: [IfStmt: [IfClause: [VarValue: [Const: foo], SubQuery: [Query: [EditTagAdd: [TagName: [Const: woot]]]]]]]',
    'Query: [IfStmt: [IfClause: [VarValue: [Const: foo], SubQuery: [Query: [EditTagAdd: [TagName: [Const: woot]]]]], SubQuery: [Query: [EditTagAdd: [TagName: [Const: nowoot]]]]]]',
    'Query: [IfStmt: [IfClause: [VarValue: [Const: foo], SubQuery: [Query: [EditTagAdd: [TagName: [Const: woot]]]]], IfClause: [DollarExpr: [ExprNode: [Const: 1, Const: -, Const: 1]], SubQuery: [Query: [EditTagAdd: [TagName: [Const: nowoot]]]]]]]',
    'Query: [IfStmt: [IfClause: [VarValue: [Const: foo], SubQuery: [Query: [EditTagAdd: [TagName: [Const: woot]]]]], IfClause: [DollarExpr: [ExprNode: [Const: 1, Const: -, Const: 1]], SubQuery: [Query: [EditTagAdd: [TagName: [Const: nowoot]]]]], SubQuery: [Query: [EditTagAdd: [TagName: [Const: nonowoot]]]]]]',
    'Query: [IfStmt: [IfClause: [DollarExpr: [ExprNode: [VarValue: [Const: data], Const: ~=, Const: hehe]], SubQuery: [Query: [VarEvalOper: [FuncCall: [VarDeref: [VarValue: [Const: lib], Const: print], CallArgs: [Const: yes], CallKwargs: []]]]]], SubQuery: [Query: [VarEvalOper: [FuncCall: [VarDeref: [VarValue: [Const: lib], Const: print], CallArgs: [Const: no], CallKwargs: []]]]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [ExprOrNode: [Const: 1, Const: or, ExprAndNode: [Const: 0, Const: and, Const: 0]]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [ExprAndNode: [UnaryExprNode: [Const: not, Const: 1], Const: and, Const: 1]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [UnaryExprNode: [Const: not, ExprNode: [Const: 1, Const: >, Const: 1]]]]]',
    'Query: [LiftTagProp: [TagProp: [TagName: [Const: baz, Const: faz], Const: lol]]]',
    'Query: [LiftFormTagProp: [FormTagProp: [Const: foo:bar, TagName: [Const: baz, Const: faz], Const: lol]]]',
    'Query: [LiftTagProp: [TagProp: [TagName: [Const: baz, Const: faz], Const: lol], Const: =, Const: 20]]',
    'Query: [LiftFormTagProp: [FormTagProp: [Const: foo:bar, TagName: [Const: baz, Const: faz], Const: lol], Const: =, Const: 20]]',
    'Query: [FiltOper: [Const: +, HasTagPropCond: [TagMatch: [Const: foo, Const: bar], Const: lol]]]',
    'Query: [FiltOper: [Const: +, TagPropCond: [TagMatch: [Const: foo, Const: bar], Const: lol, Const: =, Const: 20]]]',
    'Query: [EditTagPropDel: [TagProp: [TagName: [Const: baz, Const: faz], Const: lol]]]',
    'Query: [EditTagPropSet: [TagProp: [TagName: [Const: baz, Const: faz], Const: lol], Const: =, Const: 20]]',
    'Query: [LiftTagProp: [TagProp: [TagName: [Const: tag], Const: somegeoloctypebecauseihatelife], Const: near=, List: [VarValue: [Const: lat], VarValue: [Const: long]]]]',
    'Query: [LiftPropBy: [VarValue: [Const: foo], Const: near=, Const: 20]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, VarDeref: [VarDeref: [VarDeref: [VarDeref: [VarDeref: [VarValue: [Const: foo], Const: woot], Const: var], VarValue: [Const: bar]], Const: mar], VarValue: [Const: car]]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, VarDeref: [VarDeref: [VarValue: [Const: foo], VarValue: [Const: space key]], Const: subkey]]]',
    'Query: [ForLoop: [Const: iterkey, VarDeref: [VarDeref: [VarValue: [Const: foo], VarValue: [Const: bar key]], VarValue: [Const: biz key]], SubQuery: [Query: [LiftPropBy: [Const: inet:ipv4, Const: =, VarDeref: [VarDeref: [VarDeref: [VarValue: [Const: foo], VarValue: [Const: bar key]], VarValue: [Const: biz key]], VarValue: [Const: iterkey]]]]]]]',
    'Query: [EditParens: [EditNodeAdd: [FormName: [Const: ou:org], Const: =, Const: c71cd602f73af5bed208da21012fdf54], EditPropSet: [RelProp: [Const: loc], Const: =, Const: us]]]',
    'Query: [Function: [Const: x, FuncArgs: [Const: y, Const: z], Query: [Return: [DollarExpr: [ExprNode: [VarValue: [Const: x], Const: -, VarValue: [Const: y]]]]]]]',
    'Query: [Function: [Const: echo, FuncArgs: [Const: arg, CallKwarg: [Const: arg2, Const: default]], Query: [Return: [VarValue: [Const: arg]]]]]',
    'Query: [SetVarOper: [Const: name, Const: asdf], SetVarOper: [Const: foo, DollarExpr: [ExprDict: []]], SetItemOper: [VarValue: [Const: foo], Const: bar, Const: asdf], SetItemOper: [VarValue: [Const: foo], Const: bar baz, Const: asdf], SetItemOper: [VarValue: [Const: foo], VarValue: [Const: name], Const: asdf]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: a], SwitchCase: [FuncCall: [VarDeref: [VarValue: [Const: node], Const: form], CallArgs: [], CallKwargs: []], CaseEntry: [Const: hehe, SubQuery: [Query: [EditTagAdd: [TagName: [Const: baz]]]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: a], SwitchCase: [VarValue: [Const: woot], CaseEntry: [Const: hehe, SubQuery: [Query: [EditTagAdd: [TagName: [Const: baz]]]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: c], SwitchCase: [VarValue: [Const: woot], CaseEntry: [Const: hehe, SubQuery: [Query: [EditTagAdd: [TagName: [Const: baz]]]]], CaseEntry: [SubQuery: [Query: [EditTagAdd: [TagName: [Const: jaz]]]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: c], SwitchCase: [VarValue: [Const: woot], CaseEntry: [Const: hehe, SubQuery: [Query: [EditTagAdd: [TagName: [Const: baz]]]]], CaseEntry: [Const: haha hoho, SubQuery: [Query: [EditTagAdd: [TagName: [Const: faz]]]]], CaseEntry: [Const: lolz:lulz, SubQuery: [Query: [EditTagAdd: [TagName: [Const: jaz]]]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 1.2.3.4], SwitchCase: [VarValue: [Const: foo], CaseEntry: [Const: bar, SubQuery: [Query: [EditTagAdd: [TagName: [Const: hehe, Const: haha]]]]], CaseEntry: [Const: baz faz, SubQuery: [Query: []]]]]',

    'Query: [ForLoop: [Const: foo, VarValue: [Const: foos], SubQuery: [Query: [EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 1.2.3.4], SwitchCase: [VarValue: [Const: foo], CaseEntry: [Const: bar, SubQuery: [Query: [EditTagAdd: [TagName: [Const: ohai]], BreakOper: []]]], CaseEntry: [Const: baz, SubQuery: [Query: [EditTagAdd: [TagName: [Const: visi]], ContinueOper: []]]], CaseEntry: [Const: far, Const: faz, SubQuery: [Query: [EditTagAdd: [TagName: [Const: multi, Const: far]], ContinueOper: []]]], CaseEntry: [Const: gar, Const: gaz, SubQuery: [Query: [EditTagAdd: [TagName: [Const: multi, Const: gar]], ContinueOper: []]]], CaseEntry: [Const: har, Const: haz, SubQuery: [Query: [EditTagAdd: [TagName: [Const: multi, Const: har]], ContinueOper: []]]], CaseEntry: [Const: kar, Const: kaz, Const: koo, SubQuery: [Query: [EditTagAdd: [TagName: [Const: multi, Const: kar]], ContinueOper: []]]]], EditNodeAdd: [FormName: [Const: inet:ipv4], Const: =, Const: 5.6.7.8], EditTagAdd: [TagName: [Const: hehe]]]]]]',

    'Query: [SwitchCase: [VarValue: [Const: a], CaseEntry: [Const: a, SubQuery: [Query: []]]]]',
    'Query: [SwitchCase: [VarValue: [Const: a], CaseEntry: [Const: test:str, SubQuery: [Query: []]], CaseEntry: [SubQuery: [Query: []]]]]',
    'Query: [SwitchCase: [VarValue: [Const: a], CaseEntry: [Const: test:this:works:, SubQuery: [Query: []]], CaseEntry: [SubQuery: [Query: []]]]]',
    'Query: [SwitchCase: [VarValue: [Const: a], CaseEntry: [Const: single:quotes, SubQuery: [Query: []]], CaseEntry: [Const: doubele:quotes, SubQuery: [Query: []]], CaseEntry: [Const: noquotes, SubQuery: [Query: []]], CaseEntry: [SubQuery: [Query: []]]]]',
    'Query: [SwitchCase: [VarValue: [Const: category]], SwitchCase: [VarValue: [Const: type], CaseEntry: [SubQuery: [Query: []]]]]',
    'Query: [LiftProp: [Const: syn:tag], PivotToTags: [TagMatch: []], isjoin=True]',
    'Query: [LiftProp: [Const: syn:tag:base], PivotToTags: [TagMatch: []], isjoin=True]',
    'Query: [LiftPropBy: [Const: syn:tag:base, Const: =, Const: foo], PivotToTags: [TagMatch: []], isjoin=True]',
    'Query: [LiftPropBy: [Const: syn:tag:depth, Const: =, Const: 2], PivotToTags: [TagMatch: []], isjoin=True]',
    'Query: [LiftProp: [Const: inet:ipv4], PivotToTags: [TagMatch: []], isjoin=True]',
    'Query: [LiftProp: [Const: inet:ipv4], PivotToTags: [TagMatch: [Const: *]], isjoin=True]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.4], PivotToTags: [TagMatch: []], isjoin=True]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.4], PivotToTags: [TagMatch: [Const: *]], isjoin=True]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.4], PivotToTags: [TagMatch: [Const: biz, Const: *]], isjoin=True]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.4], PivotToTags: [TagMatch: [Const: bar, Const: baz]], isjoin=True]',
    'Query: [Function: [Const: middlechild, FuncArgs: [Const: arg2], Query: [YieldValu: [FuncCall: [VarValue: [Const: rockbottom], CallArgs: [VarValue: [Const: arg2]], CallKwargs: []]]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:comp], Const: =, List: [Const: 10, Const: bar]], SubQuery: [Query: [FormPivot: [Const: test:int], isjoin=False]]]',
    'Query: [LiftProp: [Const: test:arrayprop], FiltOper: [Const: +, ArrayCond: [RelProp: [Const: ints], Const: range=, List: [Const: 50, Const: 100]]]]',
    'Query: [LiftProp: [Const: inet:ipv4], FiltOper: [Const: +, AndCond: [VarValue: [Const: foo], VarValue: [Const: bar]]]]',
    'Query: [LiftProp: [Const: inet:ipv4], FiltOper: [Const: +, DollarExpr: [ExprAndNode: [Const: 0, Const: and, Const: 1]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprNode: [VarValue: [Const: x], Const: -, Const: 1]]]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.4], FiltOper: [Const: +, DollarExpr: [ExprNode: [ExprNode: [RelPropValue: [Const: asn], Const: +, Const: 20], Const: >=, Const: 42]]]]',
    'Query: [LiftProp: [Const: inet:ipv4], N1Walk: [Const: seen, Const: foo:bar:baz], isjoin=False]',
    'Query: [LiftProp: [Const: inet:ipv4], N1Walk: [Const: seen, List: [Const: foo:bar:baz, Const: hehe:haha:hoho], Const: ^=, Const: lol], isjoin=False]',
    "Query: [LiftProp: [Const: inet:ipv4], N1Walk: [VarList: ['foo', 'bar'], List: [VarValue: [Const: baz], VarValue: [Const: faz]], Const: =, Const: lol], isjoin=False]",
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprList: [Const: foo, Const: bar]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprList: [Const: foo, Const: bar]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprDict: [Const: foo, Const: bar, Const: baz, Const: 10]]]]',
    'Query: [SetVarOper: [Const: x, DollarExpr: [ExprDict: [Const: foo, Const: bar, Const: baz, Const: 10]]]]',
    'Query: [CmdOper: [Const: iden, List: [Const: ssl://svcrs:27492?certname=root=bar]]]',
    'Query: [SetVarOper: [Const: x, List: [Const: foo bar baz, Const: two]]]',
    'Query: [SetVarOper: [Const: foo, FormatString: [Const: foo\n    bar]]]',
    'Query: [SetVarOper: [Const: foo, List: [Const: truesec.com]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditTagPropSet: [TagProp: [TagName: [FuncCall: [VarDeref: [VarValue: [Const: tag], Const: index], CallArgs: [Const: 0], CallKwargs: []]], FuncCall: [VarDeref: [VarValue: [Const: tag], Const: index], CallArgs: [Const: 1], CallKwargs: []]], Const: =, FuncCall: [VarDeref: [VarValue: [Const: tag], Const: index], CallArgs: [Const: 2], CallKwargs: []]]]',
    'Query: [LiftFormTagProp: [FormTagProp: [Const: test:str, TagName: [FuncCall: [VarDeref: [VarValue: [Const: tag], Const: index], CallArgs: [Const: 0], CallKwargs: []]], FuncCall: [VarDeref: [VarValue: [Const: tag], Const: index], CallArgs: [Const: 1], CallKwargs: []]]]]',
    'Query: [IfStmt: [IfClause: [VarDeref: [VarValue: [Const: lib], Const: true], SubQuery: [Query: []]]], VarEvalOper: [FuncCall: [VarDeref: [VarValue: [Const: lib], Const: print], CallArgs: [FormatString: [Const: User: , VarDeref: [VarValue: [Const: lib], Const: true]]], CallKwargs: []]]]',
    'Query: [SetItemOper: [VarValue: [Const: foo], FormatString: [VarDeref: [VarValue: [Const: bar], Const: baz]], VarValue: [Const: bar]]]',
    'Query: [SetItemOper: [VarValue: [Const: foo], FormatString: [VarDeref: [VarValue: [Const: bar], Const: baz]], VarValue: [Const: bar]]]',
    'Query: [SetItemOper: [VarValue: [Const: foo], DollarExpr: [VarDeref: [VarValue: [Const: bar], Const: baz]], VarValue: [Const: bar]]]',
    'Query: [SetItemOper: [VarValue: [Const: foo], DollarExpr: [VarDeref: [VarValue: [Const: bar], Const: baz]], VarValue: [Const: bar]]]',
    'Query: [VarEvalOper: [FuncCall: [VarDeref: [VarValue: [Const: lib], Const: print], CallArgs: [VarDeref: [VarValue: [Const: foo], FormatString: [VarDeref: [VarValue: [Const: bar], Const: baz]]]], CallKwargs: []]]]',
    'Query: [VarEvalOper: [FuncCall: [VarDeref: [VarValue: [Const: lib], Const: print], CallArgs: [VarDeref: [VarValue: [Const: foo], DollarExpr: [VarDeref: [VarValue: [Const: bar], Const: baz]]]], CallKwargs: []]]]',
    'Query: [VarEvalOper: [FuncCall: [VarDeref: [VarValue: [Const: lib], Const: print], CallArgs: [FuncCall: [VarDeref: [VarDeref: [VarValue: [Const: a], DollarExpr: [Const: foo]], Const: upper], CallArgs: [], CallKwargs: []]], CallKwargs: []]]]',
    'Query: [VarEvalOper: [FuncCall: [VarDeref: [VarValue: [Const: lib], Const: print], CallArgs: [DollarExpr: [FuncCall: [VarDeref: [VarDeref: [VarValue: [Const: a], DollarExpr: [Const: foo]], Const: upper], CallArgs: [], CallKwargs: []]]], CallKwargs: []]]]',
    'Query: [VarEvalOper: [FuncCall: [VarDeref: [VarValue: [Const: lib], Const: print], CallArgs: [FuncCall: [VarDeref: [VarDeref: [VarValue: [Const: a], DollarExpr: [Const: foo]], Const: upper], CallArgs: [], CallKwargs: []]], CallKwargs: []]]]',
    'Query: [VarEvalOper: [FuncCall: [VarDeref: [VarValue: [Const: lib], Const: print], CallArgs: [DollarExpr: [FuncCall: [VarDeref: [VarDeref: [VarValue: [Const: a], DollarExpr: [Const: foo]], Const: upper], CallArgs: [], CallKwargs: []]]], CallKwargs: []]]]',
    'Query: [VarEvalOper: [FuncCall: [VarDeref: [VarValue: [Const: lib], Const: print], CallArgs: [FuncCall: [VarDeref: [DollarExpr: [Const: foo], Const: upper], CallArgs: [], CallKwargs: []]], CallKwargs: []]]]',
    'Query: [VarEvalOper: [FuncCall: [VarDeref: [VarValue: [Const: lib], Const: print], CallArgs: [DollarExpr: [FuncCall: [VarDeref: [DollarExpr: [Const: foo], Const: upper], CallArgs: [], CallKwargs: []]]], CallKwargs: []]]]',
    'Query: [VarEvalOper: [FuncCall: [VarDeref: [VarValue: [Const: lib], Const: print], CallArgs: [FuncCall: [DollarExpr: [VarValue: [Const: foo]], CallArgs: [], CallKwargs: []]], CallKwargs: []]]]',
    'Query: [VarEvalOper: [FuncCall: [VarDeref: [VarValue: [Const: lib], Const: print], CallArgs: [DollarExpr: [FuncCall: [DollarExpr: [VarValue: [Const: foo]], CallArgs: [], CallKwargs: []]]], CallKwargs: []]]]',
    'Query: [VarEvalOper: [FuncCall: [VarDeref: [VarValue: [Const: lib], Const: print], CallArgs: [FuncCall: [VarDeref: [DollarExpr: [RelPropValue: [Const: prop]], Const: upper], CallArgs: [], CallKwargs: []]], CallKwargs: []]]]',
    'Query: [VarEvalOper: [FuncCall: [VarDeref: [VarValue: [Const: lib], Const: print], CallArgs: [DollarExpr: [FuncCall: [VarDeref: [DollarExpr: [RelPropValue: [Const: prop]], Const: upper], CallArgs: [], CallKwargs: []]]], CallKwargs: []]]]',
    'Query: [VarEvalOper: [FuncCall: [VarDeref: [VarValue: [Const: lib], Const: print], CallArgs: [VarDeref: [DollarExpr: [ExprDict: [Const: unicode, Const: 1]], DollarExpr: [RelPropValue: [Const: prop]]]], CallKwargs: []]]]',
    'Query: [VarEvalOper: [FuncCall: [VarDeref: [VarValue: [Const: lib], Const: print], CallArgs: [DollarExpr: [ExprNode: [VarDeref: [DollarExpr: [ExprDict: [Const: unicode, Const: 1]], DollarExpr: [RelPropValue: [Const: prop]]], Const: +, DollarExpr: [Const: 2]]]], CallKwargs: []]]]',
    'Query: [LiftFormTag: [VarValue: [Const: form], TagName: [VarValue: [Const: tag]]]]',
    'Query: [LiftFormTagProp: [FormTagProp: [VarValue: [Const: form], TagName: [VarValue: [Const: tag]], VarValue: [Const: prop]]]]',
    'Query: [LiftProp: [Const: inet:ipv4]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.4]]',
    'Query: [LiftPropBy: [VarValue: [Const: form], Const: =, VarValue: [Const: valu]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foobar], FormPivot: [Const: inet:dns*], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foobar], FormPivot: [Const: inet:dns:*], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foobar], FormPivot: [List: [Const: meta:source, Const: inet:dns:a]], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foobar], FormPivot: [List: [Const: meta:source, Const: inet:dns*]], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foobar], FormPivot: [VarValue: [Const: foo]], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foobar], FormPivot: [Const: inet:dns*], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foobar], FormPivot: [Const: inet:dns:*], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foobar], FormPivot: [List: [Const: meta:source, Const: inet:dns:a]], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foobar], FormPivot: [List: [Const: meta:source, Const: inet:dns*]], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foobar], FormPivot: [VarValue: [Const: foo]], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foobar], N1Walk: [Const: refs, Const: inet:dns:*], isjoin=False]',
    'Query: [LiftPropBy: [Const: inet:fqdn, Const: =, Const: foo.com], PropPivot: [RelPropValue: [RelProp: [Const: zone]], List: [Const: meta:source, Const: inet:dns:a]], isjoin=False]',
    'Query: [LiftPropBy: [Const: inet:fqdn, Const: =, Const: foo.com], PropPivot: [RelPropValue: [RelProp: [Const: zone]], VarValue: [Const: foo]], isjoin=False]',
    'Query: [LiftPropBy: [Const: inet:fqdn, Const: =, Const: foo.com], PropPivot: [RelPropValue: [RelProp: [Const: zone]], List: [Const: meta:source, Const: inet:dns:a]], isjoin=True]',
    'Query: [LiftPropBy: [Const: inet:fqdn, Const: =, Const: foo.com], PropPivot: [RelPropValue: [RelProp: [Const: zone]], VarValue: [Const: foo]], isjoin=True]',
    'Query: [LiftFormTag: [Const: test:*, TagName: [Const: foo]]]',
    'Query: [LiftFormTag: [Const: test:*, TagName: [Const: foo], Const: @=, Const: 2016]]',
    'Query: [LiftFormTagProp: [FormTagProp: [Const: test:*, TagName: [Const: foo], Const: lol]]]',
    'Query: [LiftFormTagProp: [FormTagProp: [Const: test:*, TagName: [Const: foo], Const: lol], Const: =, Const: 20]]',
    'Query: [LiftProp: [Const: .created], FiltOper: [Const: +, HasAbsPropCond: [Const: inet:dns*]]]',
    'Query: [LiftProp: [Const: .created], FiltOper: [Const: -, HasAbsPropCond: [Const: inet:dns*]]]',
    'Query: [LiftProp: [Const: .created], FiltOper: [Const: +, HasAbsPropCond: [Const: inet:dns:*]]]',
    'Query: [LiftProp: [Const: .created], FiltOper: [Const: -, HasAbsPropCond: [Const: inet:dns:*]]]',
    'Query: [LiftProp: [Const: inet:ipv4], N1WalkNPivo: [], isjoin=True]',
    'Query: [LiftProp: [Const: file:bytes], N2WalkNPivo: [], isjoin=True]',
    'Query: [LiftProp: [Const: inet:asn], N2Walk: [Const: edge, Const: *], isjoin=True]',
    'Query: [LiftProp: [Const: inet:asn], N1Walk: [Const: edge, Const: *], isjoin=True]',
    "Query: [LiftProp: [Const: file:bytes], N1Walk: [VarList: ['foobar', 'bizbaz'], List: [VarValue: [Const: biz], VarValue: [Const: boz]], Const: =, Const: lol], isjoin=True]",
    'Query: [LiftProp: [Const: media:news], N2Walk: [List: [Const: neato, Const: burrito], Const: inet:fqdn], isjoin=True]',
    'Query: [LiftProp: [Const: inet:ipv4], N2Walk: [Const: *, Const: media:news], isjoin=True]',
    'Query: [LiftProp: [Const: media:news], N1Walk: [Const: *, Const: inet:fqdn], isjoin=True]',
    'Query: [LiftProp: [Const: inet:ipv4], N2Walk: [Const: *, Const: *], isjoin=True]',
    'Query: [LiftProp: [Const: media:news], N1Walk: [Const: *, Const: *], isjoin=True]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [Const: None]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [ExprDict: [Const: bar, Const: None]]]]',
    'Query: [SetVarOper: [Const: p, Const: names], LiftPropBy: [Const: ps:contact:name, Const: =, Const: foo], EditPropSet: [RelProp: [VarValue: [Const: p]], Const: ?+=, Const: bar]]',
    'Query: [SetVarOper: [Const: p, Const: names], LiftPropBy: [Const: ps:contact:name, Const: =, Const: foo], EditPropSet: [RelProp: [VarValue: [Const: p]], Const: ?-=, Const: bar]]',
    'Query: [SetVarOper: [Const: pvar, Const: stuff], LiftProp: [Const: test:arrayprop], FiltOper: [Const: +, ArrayCond: [RelProp: [VarValue: [Const: pvar]], Const: =, Const: neato]]]',
    'Query: [SetVarOper: [Const: pvar, Const: ints], LiftProp: [Const: test:arrayprop], FiltOper: [Const: +, ArrayCond: [RelProp: [VarValue: [Const: pvar]], Const: =, VarValue: [Const: othervar]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [ExprDict: [Const: foo, EmbedQuery:  inet:fqdn ]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditCondPropSet: [RelProp: [Const: hehe], CondSetOper: [Const: unset], Const: heval]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditCondPropSet: [RelProp: [Const: hehe], CondSetOper: [VarValue: [Const: foo]], Const: heval]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditCondPropSet: [RelProp: [VarValue: [Const: foo]], CondSetOper: [Const: unset], Const: heval]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditCondPropSet: [RelProp: [VarValue: [Const: foo]], CondSetOper: [VarValue: [Const: bar]], Const: heval]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditCondPropSet: [RelProp: [VarValue: [Const: foo]], CondSetOper: [VarDeref: [VarValue: [Const: bar], Const: baz]], Const: heval]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditCondPropSet: [RelProp: [VarValue: [Const: foo]], CondSetOper: [VarDeref: [VarValue: [Const: bar], DollarExpr: [Const: baz]]], Const: heval]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditCondPropSet: [RelProp: [VarValue: [Const: foo]], CondSetOper: [FuncCall: [VarDeref: [VarValue: [Const: bar], Const: baz], CallArgs: [], CallKwargs: []]], Const: heval]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditEdgeAdd: [Const: refs, VarValue: [Const: n]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditEdgeAdd: [Const: refs, FuncCall: [VarDeref: [VarValue: [Const: n], Const: baz], CallArgs: [], CallKwargs: []]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditEdgeDel: [Const: refs, VarValue: [Const: n]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditEdgeAdd: [Const: refs, VarValue: [Const: n]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditEdgeAdd: [Const: refs, FuncCall: [VarDeref: [VarValue: [Const: n], Const: baz], CallArgs: [], CallKwargs: []]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditEdgeDel: [Const: refs, VarValue: [Const: n]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditPropSetMulti: [RelProp: [Const: bar], Const: ++=, DollarExpr: [ExprList: [Const: 1, Const: 2]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditPropSetMulti: [RelProp: [VarValue: [Const: foo]], Const: ++=, DollarExpr: [ExprList: [Const: 1, Const: 2]]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditPropSetMulti: [RelProp: [Const: bar], Const: --=, List: [Const: foo, Const: bar]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditPropSetMulti: [RelProp: [Const: bar], Const: ?++=, VarValue: [Const: baz]]]',
    'Query: [EditNodeAdd: [FormName: [Const: test:str], Const: =, Const: foo], EditPropSetMulti: [RelProp: [Const: bar], Const: ?--=, SubQuery: [Query: [EditNodeAdd: [FormName: [Const: it:dev:str], Const: =, Const: foo]]]]]',
    'Query: [SetVarOper: [Const: foo, List: [Const: notime]]]',
    'Query: [SetVarOper: [Const: foo, List: [Const: nulltime]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [UnaryExprNode: [Const: not, VarValue: [Const: x]]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [UnaryExprNode: [Const: not, VarValue: [Const: x]]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [UnaryExprNode: [Const: not, DollarExpr: [VarValue: [Const: x]]]]]]',
    'Query: [SetVarOper: [Const: foo, DollarExpr: [UnaryExprNode: [Const: not, DollarExpr: [VarValue: [Const: x]]]]]]',
]

class GrammarTest(s_t_utils.SynTest):

    def test_grammar(self):
        '''
        Validates that we have no grammar ambiguities
        '''
        with s_datfile.openDatFile('synapse.lib/storm.lark') as larkf:
            grammar = larkf.read().decode()

        parser = lark.Lark(grammar, start='query', debug=True, regex=True, parser='lalr',
                           keep_all_tokens=True, maybe_placeholders=False,
                           propagate_positions=True)

        for term, valu in parser._terminals_dict.items():
            self.false(term.startswith('__ANON'), msg=f'ANON token {valu} present in grammar!')

        for i, query in enumerate(Queries):
            try:
                tree = parser.parse(query)
                # print(f'#{i}: {query}')
                # print(tree, '\n')
                self.notin('_ambig', str(tree))

            except (lark.ParseError, lark.UnexpectedCharacters):
                print(f'Failure on parsing #{i}:\n{{{query}}}')
                raise

    async def test_parser(self):
        self.maxDiff = None
        for i, query in enumerate(Queries):
            parser = s_parser.Parser(query)
            tree = parser.query()
            self.eq(str(tree), _ParseResults[i])

    def test_cmdrargs(self):
        q = '''add {inet:fqdn | graph 2 --filter { -#nope } } inet:f-M +1 { [ meta:note='*' :type=m1]}'''
        correct = (
            'add',
            'inet:fqdn | graph 2 --filter { -#nope }',
            'inet:f-M',
            '+1',
            "[ meta:note='*' :type=m1]"
            )
        parser = s_parser.Parser(q)
        args = parser.cmdrargs()
        self.eq(args, correct)

        q = 'add --filter={inet:fqdn | limit 1}'
        parser = s_parser.Parser(q)
        args = parser.cmdrargs()
        self.eq(args, ['add', '--filter=inet:fqdn | limit 1'])

        query = 'add {uniq +#*}'
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            parser.cmdrargs()

    def test_mode_lookup(self):
        q = '1.2.3.4 vertex.link | spin'
        parser = s_parser.Parser(q)
        tree = parser.lookup()
        self.eq(str(tree), 'Lookup: [LookList: [Const: 1.2.3.4, Const: vertex.link], '
                           'Query: [CmdOper: [Const: spin, Const: ()]]]')

        query = '1.2.3.4 | uniq +#*'
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            parser.lookup()

    def test_mode_search(self):
        tree = s_parser.parseQuery('foo bar | spin', mode='search')
        self.eq(str(tree), 'Search: [LookList: [Const: foo, Const: bar], '
                           'Query: [CmdOper: [Const: spin, Const: ()]]]')

        query = '1.2.3.4 | uniq +#*'
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            parser.search()

    def test_mode_storm(self):
        # added for coverage of the top level function...
        tree = s_parser.parseQuery('inet:fqdn=vertex.link', mode='storm')
        self.eq(str(tree), 'Query: [LiftPropBy: [Const: inet:fqdn, Const: =, Const: vertex.link]]')

    def test_mode_autoadd(self):
        # added for coverage of the top level function...
        tree = s_parser.parseQuery('vertex.link', mode='autoadd')
        self.eq(str(tree), 'Lookup: [LookList: [Const: vertex.link]]')

    def test_parse_float(self):
        self.raises(s_exc.BadSyntax, s_grammar.parse_float, 'visi', 0)
        self.eq((4.2, 3), s_grammar.parse_float('4.2', 0))
        self.eq((-4.2, 4), s_grammar.parse_float('-4.2', 0))
        self.eq((-4.2, 8), s_grammar.parse_float('    -4.2', 0))
        self.eq((-4.2, 8), s_grammar.parse_float('    -4.2', 2))

    def test_nom(self):
        self.eq(('xyz', 10), s_grammar.nom('   xyz    ', 0, 'wxyz', trim=True))

    def test_parse_cmd_string(self):
        self.eq(('newp', 9), s_parser.parse_cmd_string('help newp', 5))

    async def test_syntax_error(self):

        query = 'test:str )'
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            parser.query()
        errinfo = cm.exception.errinfo

        self.eq(errinfo.get('at'), 9)
        self.eq(errinfo.get('line'), 1)
        self.eq(errinfo.get('column'), 10)
        self.true(errinfo.get('mesg').startswith("Unexpected token ')' at line 1, column 10"))

        query = 'test:str {'
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            parser.query()
        errinfo = cm.exception.errinfo

        self.eq(errinfo.get('at'), 9)
        self.eq(errinfo.get('line'), 1)
        self.eq(errinfo.get('column'), 10)
        self.true(errinfo.get('mesg').startswith("Unexpected token 'end of input' at line 1, column 10"))

        query = '''function itworks() {
                $lib.print('it works')
                return ( $lib.true )
            }

            $itworks()

            function foo(baz=$lib.true, faz) {
                return ( $lib.true )
            }

            $foo()'''
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            parser.query()
        errinfo = cm.exception.errinfo
        self.eq(errinfo.get('at'), 160)
        self.eq(errinfo.get('line'), 8)
        self.eq(errinfo.get('column'), 25)
        self.eq(errinfo.get('mesg'),
                'Positional parameter "faz" follows keyword parameter in definition')

        query = '''function foo(bar, baz, bar) { return ( $lib.true ) }'''
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            parser.query()
        errinfo = cm.exception.errinfo
        self.nn(errinfo.get('highlight'))
        self.eq(errinfo.get('at'), 23)
        self.eq(errinfo.get('line'), 1)
        self.eq(errinfo.get('column'), 24)
        self.eq(errinfo.get('mesg'),
                'Duplicate parameter "bar" in function definition')

        query = '''$lib.foo(bar=(1), baz=(2), bar=(3))'''
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            parser.query()
        errinfo = cm.exception.errinfo
        self.eq(errinfo.get('at'), 27)
        self.eq(errinfo.get('line'), 1)
        self.eq(errinfo.get('column'), 28)
        self.eq(errinfo.get('mesg'),
                'Duplicate keyword argument "bar" in function call')

        query = '''$lib.foo(bar=(1), (2), (3))'''
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            parser.query()
        errinfo = cm.exception.errinfo
        self.eq(errinfo.get('at'), 18)
        self.eq(errinfo.get('line'), 1)
        self.eq(errinfo.get('column'), 19)
        self.eq(errinfo.get('mesg'),
                "Positional argument follows keyword argument in function call")

        query = '''

        { inet:cidr4#rep.some.body
        $lib.print('weee')
        tee { -> :network } }
        '''
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            parser.query()
        errinfo = cm.exception.errinfo
        self.eq(errinfo.get('at'), 81)
        self.eq(errinfo.get('line'), 5)
        self.eq(errinfo.get('column'), 18)
        self.eq(errinfo.get('token'), ':network')
        self.true(errinfo.get('mesg').startswith("Unexpected token 'relative property name' at line 5, column 18"))

        query = 'inet:ipv4 | tee { -> foo '
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            _ = parser.query()
        errinfo = cm.exception.errinfo
        self.eq(errinfo.get('at'), 21)
        self.eq(errinfo.get('line'), 1)
        self.eq(errinfo.get('column'), 22)
        self.eq(errinfo.get('token'), 'foo')
        self.true(errinfo.get('mesg').startswith("Unexpected token 'command name' at line 1, column 22"))

        query = '''// comment

        #rep.blah.newp +inet:ipv4 --> * <--'''
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            _ = parser.query()
        errinfo = cm.exception.errinfo
        self.eq(errinfo.get('at'), 52)
        self.eq(errinfo.get('line'), 3)
        self.eq(errinfo.get('column'), 41)
        self.true(errinfo.get('mesg').startswith("Unexpected token 'end of input' at line 3, column 41"))

        query = '''// comment

                #rep.blah.newp +inet:ipv4 --> * <-- | help'''
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            _ = parser.query()
        errinfo = cm.exception.errinfo
        self.eq(errinfo.get('at'), 64)
        self.eq(errinfo.get('line'), 3)
        self.eq(errinfo.get('column'), 53)
        self.true(errinfo.get('mesg').startswith("Unexpected token '|' at line 3, column 53"))

        query = '''$str = $lib.cast(str,(1234))
         if (!$str ~= '3.+0'  ) {
           $lib.print($str)
         }'''

        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            _ = parser.query()
        errinfo = cm.exception.errinfo
        self.eq(errinfo.get('at'), 42)
        self.eq(errinfo.get('line'), 2)
        self.eq(errinfo.get('column'), 14)
        self.true(errinfo.get('mesg').startswith("Unexpected token 'comparison operator' at line 2, column 14"))

        query = '''$str = $lib.cast(str, (1234))  if (!$str ~= '3.+0'  ) { $lib.print($str) }'''
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            _ = parser.query()
        errinfo = cm.exception.errinfo
        self.eq(errinfo.get('at'), 35)
        self.eq(errinfo.get('line'), 1)
        self.eq(errinfo.get('column'), 36)
        self.true(errinfo.get('mesg').startswith("Unexpected token 'comparison operator' at line 1, column 36"))

        query = '''return(({"foo": "bar", "baz": foo}))'''
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            _ = parser.query()
        errinfo = cm.exception.errinfo
        self.eq(errinfo.get('at'), 30)
        self.eq(errinfo.get('line'), 1)
        self.eq(errinfo.get('column'), 31)
        self.true(errinfo.get('mesg').startswith("Unexpected unquoted string in JSON expression"))

        query = '''ou:name="foo\x00bar"'''
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            _ = parser.query()
        errinfo = cm.exception.errinfo
        self.eq(errinfo.get('valu'), '\'"foo\\x00bar"\'')
        self.true(errinfo.get('mesg').startswith('Invalid character in string \'"foo\\x00bar"\''))

        query = '''#test.*.bar'''
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            _ = parser.query()
        errinfo = cm.exception.errinfo
        self.true(errinfo.get('mesg').startswith("Unexpected token 'default case' at line 1, column 7"))

        query = '''$foo=(3+foo)'''
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            _ = parser.query()
        errinfo = cm.exception.errinfo
        self.eq(1, errinfo.get('mesg').count('#'))

        query = '$q = ${ /* secret comment */ $lib.print([hello) } $lib.macro.set(hehe, $q)'
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            _ = parser.query()
        info = cm.exception.errinfo.get('highlight')
        self.eq((40, 41), info['offsets'])
        self.eq((1, 1), info['lines'])
        self.eq((41, 42), info['columns'])

        query = """function test(hello) {
                    +'''asdf
                    asdfasdf'''
        }"""
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            _ = parser.query()
        info = cm.exception.errinfo.get('highlight')
        self.eq((44, 83), info['offsets'])
        self.eq((2, 3), info['lines'])
        self.eq((22, 31), info['columns'])

        query = '$x=$lib.guid(foo$bar)'
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            _ = parser.query()
        errinfo = cm.exception.errinfo
        self.true(errinfo.get('mesg').startswith("Unexpected token '$' at line 1, column 17"))

        query = '$x=$lib.guid(foo(bar)'
        parser = s_parser.Parser(query)
        with self.raises(s_exc.BadSyntax) as cm:
            _ = parser.query()
        errinfo = cm.exception.errinfo
        self.true(errinfo.get('mesg').startswith("Unexpected token '(' at line 1, column 17"))

    async def test_quotes(self):

        # Test vectors
        queries = ((r'''[test:str="WORDS \"THINGS STUFF.\""]''', 'WORDS "THINGS STUFF."'),
                   (r'''[test:str='WORDS "THINGS STUFF."']''', 'WORDS "THINGS STUFF."'),
                   (r'''[test:str="\""]''', '"'),
                   (r'''[test:str="hello\\world!"]''', 'hello\\world!'),
                   (r'''[test:str="hello\\\"world!"]''', 'hello\\"world!'),
                   # Single quoted string
                   (r'''[test:str='hello\\\"world!']''', 'hello\\\\\\"world!'),
                   (r'''[test:str='hello\t"world!']''', 'hello\\t"world!'),
                   # TAB
                   (r'''[test:str="hello\tworld!"]''', 'hello\tworld!'),
                   (r'''[test:str="hello\\tworld!"]''', 'hello\\tworld!'),
                   (r'''[test:str="hello\\\tworld!"]''', 'hello\\\tworld!'),
                   # LF / Newline
                   (r'''[test:str="hello\nworld!"]''', 'hello\nworld!'),
                   (r'''[test:str="hello\\nworld!"]''', 'hello\\nworld!'),
                   (r'''[test:str="hello\\\nworld!"]''', 'hello\\\nworld!'),
                   # CR / Carriage returns
                   (r'''[test:str="hello\rworld!"]''', 'hello\rworld!'),
                   (r'''[test:str="hello\\rworld!"]''', 'hello\\rworld!'),
                   (r'''[test:str="hello\\\rworld!"]''', 'hello\\\rworld!'),
                   # single quote escape
                   (r'''[test:str="hello\'world!"]''', '''hello'world!'''),
                   (r'''[test:str="hello'world!"]''', '''hello'world!'''),  # escape isn't technically required
                   # BEL
                   (r'''[test:str="hello\aworld!"]''', '''hello\aworld!'''),
                   # BS
                   (r'''[test:str="hello\bworld!"]''', '''hello\bworld!'''),
                   # FF
                   (r'''[test:str="hello\fworld!"]''', '''hello\fworld!'''),
                   # VT
                   (r'''[test:str="hello\vworld!"]''', '''hello\vworld!'''),
                   # \xhh - hex
                   (r'''[test:str="hello\xffworld!"]''', '''hello\xffworld!'''),
                   # \ooo - octal
                   (r'''[test:str="hello\040world!"]''', '''hello world!'''),
                   # Items encoded as a python literal object wrapped in quotes
                   # are not turned into their corresponding item, they are
                   # treated as strings.
                   (r'''[test:str="{'key': 'valu'}"]''', '''{'key': 'valu'}'''),
                   )

        async with self.getTestCore() as core:
            for (query, valu) in queries:
                nodes = await core.nodes(query)
                self.len(1, nodes)
                self.eq(nodes[0].ndef[1], valu)

    def test_isre_funcs(self):

        self.true(s_grammar.isCmdName('testcmd'))
        self.true(s_grammar.isCmdName('testcmd2'))
        self.true(s_grammar.isCmdName('testcmd.yup'))
        self.false(s_grammar.isCmdName('2testcmd'))
        self.false(s_grammar.isCmdName('testcmd:newp'))
        self.false(s_grammar.isCmdName('.hehe'))

        self.true(s_grammar.isUnivName('.hehe'))
        self.true(s_grammar.isUnivName('.hehe:haha'))
        self.true(s_grammar.isUnivName('.hehe.haha'))
        self.true(s_grammar.isUnivName('.hehe4'))
        self.true(s_grammar.isUnivName('.hehe.4haha'))
        self.true(s_grammar.isUnivName('.hehe:4haha'))
        self.false(s_grammar.isUnivName('.4hehe'))
        self.false(s_grammar.isUnivName('test:str'))
        self.false(s_grammar.isUnivName('test:str.hehe'))
        self.false(s_grammar.isUnivName('test:str.hehe:haha'))
        self.false(s_grammar.isUnivName('test:str.haha.hehe'))
        self.true(s_grammar.isUnivName('.foo:x'))
        self.true(s_grammar.isUnivName('.x:foo'))
        self.true(s_grammar.isUnivName('._haha'))

        self.true(s_grammar.isFormName('test:str'))
        self.true(s_grammar.isFormName('t2:str'))
        self.true(s_grammar.isFormName('test:str:yup'))
        self.true(s_grammar.isFormName('test:str123'))
        self.false(s_grammar.isFormName('test'))
        self.false(s_grammar.isFormName('2t:str'))
        self.false(s_grammar.isFormName('.hehe'))
        self.false(s_grammar.isFormName('testcmd'))
        self.true(s_grammar.isFormName('x:foo'))
        self.true(s_grammar.isFormName('foo:x'))

        self.true(s_grammar.isPropName('test:str'))
        self.true(s_grammar.isPropName('test:str:tick'))
        self.true(s_grammar.isPropName('test:str:_tick'))
        self.true(s_grammar.isPropName('_test:str:_tick'))
        self.true(s_grammar.isPropName('test:str:str123'))
        self.true(s_grammar.isPropName('test:str:123str'))
        self.true(s_grammar.isPropName('test:str:123:456'))
        self.true(s_grammar.isPropName('test:str.hehe'))
        self.true(s_grammar.isPropName('test:str.hehe'))
        self.true(s_grammar.isPropName('test:str.hehe.haha'))
        self.true(s_grammar.isPropName('test:str.hehe:haha'))
        self.true(s_grammar.isPropName('test:x'))
        self.true(s_grammar.isPropName('x:x'))
        self.false(s_grammar.isPropName('test'))
        self.false(s_grammar.isPropName('2t:str'))
        self.false(s_grammar.isPropName('.hehe'))
        self.false(s_grammar.isPropName('testcmd'))

    async def test_embed_offsets(self):

        embq = ' /* secret comment */ $lib.print(hello) /* haha */ $lib.print(goodbye) /*foo */ '
        query = f'$q = ${{{embq}}} $lib.print($q)'
        parser = s_parser.Parser(query)
        q = parser.query()
        embed = q.kids[0].kids[1]
        self.eq(embq, embed.getAstText())

def gen_parse_list():
    '''
    Prints out the Asts for a list of queries in order to compare ASTs between versions of parsers
    '''
    retn = []
    for i, query in enumerate(Queries):
        parser = s_parser.Parser(query)
        tree = parser.query()
        retn.append(str(tree))
    return retn

def print_parse_list():
    for i in gen_parse_list():
        print(f'    {repr(i)},')

if __name__ == '__main__':
    print_parse_list()
