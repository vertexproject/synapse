import unittest

import lark  # type: ignore


import synapse.exc as s_exc

import synapse.lib.datfile as s_datfile
import synapse.lib.grammar as s_grammar

import synapse.tests.utils as s_t_utils

# flake8: noqa: E501

_Queries = [
    'inet:fqdn#xxx.xxxxxx.xxxx.xx for $tag in $node.tags(xxx.xxxxxx.*.xx) { <- edge:refs +#xx <- graph:cluster [ +#foo]  ->edge:refs }',
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
    'test:migr <- edge:refs',
    '#test.bar -#test -+> *',
    '#test.bar -#test -> *',
    '#test.bar -#test <+- *',
    '#test.bar -#test <- *',
    '$bar=5.5.5.5 [ inet:ipv4=$bar ]',
    '$blah = $lib.dict(foo=vertex.link) [ inet:fqdn=$blah.foo ]',
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
    "[graph:node='*' :type=m1]",
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
    '[edge:has=((test:str, foobar), (test:str, foo))]',
    '[edge:refs=((test:comp, (2048, horton)), (test:comp, (4096, whoville)))]',
    '[edge:refs=((test:comp, (9001, "A mean one")), (test:comp, (40000, greeneggs)))]',
    '[edge:refs=((test:int, 16), (test:comp, (9999, greenham)))]',
    '[edge:refs=((test:str, 123), (test:int, 123))]',
    '[inet:dns:query=(tcp://1.2.3.4, "", 1)]',
    '[inet:dns:query=(tcp://1.2.3.4, "foo*.haha.com", 1)]',
    '[inet:ipv4=1.2.3.1-1.2.3.3]',
    '[inet:ipv4=1.2.3.4 :asn=10] [meta:seen=(abcd, (inet:asn, 10))]',
    '[meta:seen=(abcd, (test:str, pennywise))]',
    '[meta:source=abcd +#omit.nopiv] [meta:seen=(abcd, (test:pivtarg, foo))]',
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
    '[test:str=a] switch $woot { hehe: {[+#baz]} }',
    '[test:str=beep test:str=boop]',
    '[test:str=c] switch $woot { hehe: {[+#baz]} *: {[+#jaz]} }',
    '[test:str=c] switch $woot { hehe: {[+#baz]} haha hoho: {[+#faz]} "lolz:lulz": {[+#jaz]} }',
    '[test:str=foo :tick=201808021201]',
    '[test:str=hehe] | iden abcd | count',
    '[test:str=hello]',
    'edge:refs +:n1*range=((test:comp, (1000, green)), (test:comp, (3000, ham)))',
    'edge:refs',
    'edge:wentto',
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
    'geo:place=$place <- edge:has <- *',
    'geo:place=$place <- edge:has <- ps:person',
    'geo:place=abcd $latlong=:latlong $radius=:radius | spin | tel:mob:telem:latlong*near=($latlong, 3km)',
    'graph:cluster=abcd | noderefs -d 2 --join',
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
    'meta:seen:meta:source=$sorc -> *',
    'meta:seen:meta:source=$sorc :node -> *',
    'meta:source=8f1401de15918358d5247e21ca29a814',
    'movetag #a.b #a.m',
    'movetag #hehe #woot',
    'ps:person=$pers -> edge:has -> *',
    'ps:person=$pers -> edge:has -> geo:place',
    'ps:person=$pers -> edge:wentto +:time@=(2014,2017) -> geo:place',
    'ps:person=$pers -> edge:wentto -> *',
    'ps:person=$pers -> edge:wentto :n2 -> *',
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
    'test:str +:.seen*range=((20090601, 20090701), (20110905, 20110906,))',
    'test:str +:bar*range=((test:str, c), (test:str, q))',
    'test:str +:tick*range=(19701125, 20151212)',
    'test:str +:tick=($test, "+- 2day")',
    'test:str +:tick=(2015, "+1 day")',
    'test:str +:tick=(20150102, "-3 day")',
    'test:str +:tick=(20150201, "+1 day")',
    'test:str +:tick=2015',
    'test:str +:tick@=("-1 day")',
    'test:str +:tick@=("now+2days", "-3 day")',
    'test:str +:tick@=("now-1day", "?")',
    'test:str +:tick@=(2015)',
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
    'test:str=foo <+- edge:has',
    'test:str=foo <- edge:has',
    'test:str=foo | delnode',
    'test:str=foobar -+> edge:has',
    'test:str=foobar -> edge:has <+- test:str',
    'test:str=foobar -> edge:has <- test:str',
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
            baz faz: {}
        } ''',
    '''
        inet:fqdn | graph
                    --degrees 2
                    --filter { -#nope }
                    --pivot { <- meta:seen <- meta:source }
                    --form-pivot inet:fqdn {<- * | limit 20}
                    --form-pivot inet:fqdn {-> * | limit 20}
                    --form-filter inet:fqdn {-inet:fqdn:issuffix=1}
                    --form-pivot syn:tag {-> *}
                    --form-pivot * {-> #} ''',
    '''
        for $foo in $foos {

            [ inet:ipv4=1.2.3.4 ]

            switch $foo {
                bar: { [ +#ohai ] break }
                baz: { [ +#visi ] continue }
            }

            [ inet:ipv4=5.6.7.8 ]
            [ +#hehe ]
        } ''',
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

    {[ edge:has=($node, ('inet:email:header', ('to', 'Visi Kensho <visi@vertex.link>'))) ]}
    ''',
    '$x = $(1 / 3)',
    '$x = $(1 * 3)',
    '$x = $(1 * 3 + 2)',
    '$x = $(1 -3.2 / -3.2)',
    '$x = $(1 + 3 / 2    )',
    '$x = $((1 + 3)/ 2)',
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
]

# Generated with print_parse_list below
_ParseResults = [
    'Query: [LiftFormTag: [Const: inet:fqdn, TagName: xxx.xxxxxx.xxxx.xx], ForLoop: [Const: tag, FuncCall: [VarDeref: [VarValue: [Const: node], Const: tags], CallArgs: [Const: xxx.xxxxxx.*.xx], CallKwargs: []], SubQuery: [Query: [PivotInFrom: [AbsProp: edge:refs], isjoin=False, FiltOper: [Const: +, TagCond: [TagMatch: xx]], PivotInFrom: [AbsProp: graph:cluster], isjoin=False, EditTagAdd: [TagName: foo], FormPivot: [AbsProp: edge:refs], isjoin=False]]]]',
    'Query: [FiltOper: [Const: +, AbsPropCond: [AbsProp: syn:tag, Const: ~=, Const: aka.*.mal.*]]]',
    'Query: [FiltOper: [Const: +, OrCond: [OrCond: [AbsPropCond: [AbsProp: syn:tag, Const: ^=, Const: aka], AbsPropCond: [AbsProp: syn:tag, Const: ^=, Const: cno]], AbsPropCond: [AbsProp: syn:tag, Const: ^=, Const: rep]]]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: foo], EditNodeAdd: [AbsProp: test:int, Const: 42]]',
    'Query: [CmdOper: [Const: help, Const: ()]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: abcd], EditPropSet: [RelProp: tick, Const: 2015], EditTagAdd: [TagName: cool]]',
    'Query: [SubQuery: [Query: [LiftTag: [TagName: baz]]], LiftPropBy: [Const: test:str, Const: =, Const: foo]]',
    'Query: [LiftTagTag: [TagName: baz.faz]]',
    'Query: [LiftTag: [VarValue: [Const: tag]], EditTagDel: [VarValue: [Const: tag]]]',
    'Query: [LiftTag: [VarValue: [Const: tag]]]',
    'Query: [LiftTag: [TagName: foo]]',
    'Query: [LiftTag: [TagName: foo]]',
    'Query: [LiftTag: [TagName: foo]]',
    'Query: [LiftTag: [TagName: hehe.haha]]',
    'Query: [VarEvalOper: [VarDeref: [VarValue: [Const: hehe], Const: haha]]]',
    'Query: [LiftTag: [TagName: test.bar], FiltOper: [Const: +, HasAbsPropCond: [AbsProp: test:pivcomp]], PivotOut: [], isjoin=True]',
    'Query: [LiftTag: [TagName: test.bar], FiltOper: [Const: +, HasAbsPropCond: [AbsProp: test:pivcomp]], PivotOut: [], isjoin=False]',
    'Query: [LiftTag: [TagName: test.bar], FiltOper: [Const: +, HasAbsPropCond: [AbsProp: test:str]], PivotIn: [], isjoin=True]',
    'Query: [LiftTag: [TagName: test.bar], FiltOper: [Const: +, HasAbsPropCond: [AbsProp: test:str]], PivotIn: [], isjoin=False]',
    'Query: [LiftProp: [Const: test:migr], PivotInFrom: [AbsProp: edge:refs], isjoin=False]',
    'Query: [LiftTag: [TagName: test.bar], FiltOper: [Const: -, TagCond: [TagMatch: test]], PivotOut: [], isjoin=True]',
    'Query: [LiftTag: [TagName: test.bar], FiltOper: [Const: -, TagCond: [TagMatch: test]], PivotOut: [], isjoin=False]',
    'Query: [LiftTag: [TagName: test.bar], FiltOper: [Const: -, TagCond: [TagMatch: test]], PivotIn: [], isjoin=True]',
    'Query: [LiftTag: [TagName: test.bar], FiltOper: [Const: -, TagCond: [TagMatch: test]], PivotIn: [], isjoin=False]',
    'Query: [VarSetOper: [Const: bar, Const: 5.5.5.5], EditNodeAdd: [AbsProp: inet:ipv4, VarValue: [Const: bar]]]',
    'Query: [VarSetOper: [Const: blah, FuncCall: [VarDeref: [VarValue: [Const: lib], Const: dict], CallArgs: [], CallKwargs: [CallKwarg: [Const: foo, Const: vertex.link]]]], EditNodeAdd: [AbsProp: inet:fqdn, VarDeref: [VarValue: [Const: blah], Const: foo]]]',
    "Query: [VarListSetOper: [VarList: ['tick', 'tock'], UnivPropValue: [UnivProp: .seen]]]",
    'Query: [LiftProp: [Const: .created]]',
    'Query: [LiftPropBy: [Const: .created, Const: <, Const: 2010]]',
    'Query: [LiftPropBy: [Const: .created, Const: >, Const: 2010]]',
    'Query: [LiftPropBy: [Const: .created, Const: *range=, List: [Const: 2010, Const: ?]]]',
    'Query: [LiftPropBy: [Const: .created, Const: *range=, List: [Const: 2010, Const: 3001]]]',
    'Query: [LiftPropBy: [Const: .created, Const: =, Const: 2001]]',
    'Query: [LiftPropBy: [Const: .created, Const: =, Const: {created}]]',
    'Query: [LiftProp: [Const: .seen], EditUnivDel: [UnivProp: .seen]]',
    'Query: [LiftPropBy: [Const: .seen, Const: ~=, Const: ^r]]',
    'Query: [EditNodeAdd: [AbsProp: graph:node, Const: *], EditPropSet: [RelProp: type, Const: m1]]',
    'Query: [EditNodeAdd: [AbsProp: geo:place, Const: *], EditPropSet: [RelProp: latlong, List: [Const: -30.0, Const: 20.22]]]',
    'Query: [EditNodeAdd: [AbsProp: inet:asn, Const: 200], EditPropSet: [RelProp: name, Const: visi]]',
    'Query: [EditNodeAdd: [AbsProp: inet:dns:a, List: [Const: woot.com, Const: 12.34.56.78]]]',
    'Query: [EditNodeAdd: [AbsProp: inet:dns:a, FuncCall: [VarDeref: [VarValue: [Const: blob], Const: split], CallArgs: [Const: |], CallKwargs: []]]]',
    'Query: [EditNodeAdd: [AbsProp: inet:dns:a, List: [Const: vertex.link, Const: 5.5.5.5]], EditTagAdd: [TagName: nope]]',
    'Query: [EditNodeAdd: [AbsProp: inet:dns:a, List: [Const: woot.com, Const: 1.2.3.4]]]',
    'Query: [EditNodeAdd: [AbsProp: inet:dns:a, List: [Const: woot.com, Const: 1.2.3.4]], EditTagAdd: [TagName: yepr]]',
    'Query: [EditNodeAdd: [AbsProp: inet:dns:a, List: [Const: woot.com, Const: 1.2.3.4]], EditNodeAdd: [AbsProp: inet:dns:a, List: [Const: vertex.link, Const: 1.2.3.4]]]',
    'Query: [EditNodeAdd: [AbsProp: inet:dns:a, List: [Const: woot.com, Const: 1.2.3.4]], EditPropSet: [UnivProp: .seen, List: [Const: 2015, Const: 2016]]]',
    'Query: [EditNodeAdd: [AbsProp: inet:fqdn, Const: hehe.com], EditNodeAdd: [AbsProp: inet:ipv4, Const: 127.0.0.1], EditNodeAdd: [AbsProp: hash:md5, Const: d41d8cd98f00b204e9800998ecf8427e]]',
    'Query: [EditNodeAdd: [AbsProp: inet:fqdn, Const: woot.com]]',
    'Query: [EditNodeAdd: [AbsProp: inet:fqdn, Const: vertex.link], EditNodeAdd: [AbsProp: inet:ipv4, Const: 1.2.3.4]]',
    'Query: [EditNodeAdd: [AbsProp: inet:fqdn, Const: woot.com], EditTagAdd: [TagName: bad, List: [Const: 2015, Const: 2016]]]',
    'Query: [EditNodeAdd: [AbsProp: inet:fqdn, Const: woot.com], PivotOut: [], isjoin=False]',
    'Query: [EditNodeAdd: [AbsProp: inet:fqdn, Const: woot.com], EditNodeAdd: [AbsProp: inet:fqdn, Const: vertex.link], EditNodeAdd: [AbsProp: inet:user, RelPropValue: [RelProp: zone]], FiltOper: [Const: +, HasAbsPropCond: [AbsProp: inet:user]]]',
    'Query: [EditNodeAdd: [AbsProp: inet:ipv4, Const: 94.75.194.194], EditPropSet: [RelProp: loc, Const: nl]]',
    'Query: [EditNodeAdd: [AbsProp: inet:ipv4, VarValue: [Const: foo]]]',
    'Query: [EditNodeAdd: [AbsProp: test:int, VarDeref: [VarValue: [Const: hehe], Const: haha]]]',
    'Query: [EditNodeAdd: [AbsProp: inet:ipv4, Const: 1.2.3.0/30], EditNodeAdd: [AbsProp: inet:ipv4, Const: 5.5.5.5]]',
    'Query: [EditNodeAdd: [AbsProp: inet:ipv4, Const: 1.2.3.4], EditPropSet: [RelProp: asn, Const: 2]]',
    'Query: [EditNodeAdd: [AbsProp: inet:ipv4, Const: 1.2.3.4], EditPropSet: [RelProp: loc, Const: us], EditNodeAdd: [AbsProp: inet:dns:a, List: [Const: vertex.link, Const: 1.2.3.4]]]',
    'Query: [EditNodeAdd: [AbsProp: inet:ipv4, Const: 1.2.3.4]]',
    'Query: [EditNodeAdd: [AbsProp: inet:ipv4, Const: 192.168.1.0/24]]',
    'Query: [EditNodeAdd: [AbsProp: inet:ipv4, Const: 4.3.2.1], EditPropSet: [RelProp: loc, Const: zz], EditNodeAdd: [AbsProp: inet:dns:a, List: [Const: example.com, Const: 4.3.2.1]]]',
    'Query: [EditNodeAdd: [AbsProp: inet:ipv4, Const: 197.231.221.211], EditPropSet: [RelProp: asn, Const: 37560], EditPropSet: [RelProp: loc, Const: lr.lo.voinjama], EditPropSet: [RelProp: latlong, Const: 8.4219,-9.7478], EditPropSet: [RelProp: dns:rev, Const: exit1.ipredator.se], EditTagAdd: [TagName: cno.anon.tor.exit, List: [Const: 2017/12/19, Const: 2019/02/15]]]',
    'Query: [EditNodeAdd: [AbsProp: inet:user, Const: visi], EditNodeAdd: [AbsProp: inet:user, Const: whippit]]',
    'Query: [EditNodeAdd: [AbsProp: test:comp, List: [Const: 10, Const: haha]], EditTagAdd: [TagName: foo.bar], EditTagDel: [TagName: foo.bar]]',
    'Query: [EditNodeAdd: [AbsProp: test:comp, List: [Const: 127, Const: newp]], EditNodeAdd: [AbsProp: test:comp, List: [Const: 127, Const: 127]]]',
    'Query: [EditNodeAdd: [AbsProp: test:comp, List: [Const: 123, Const: test]], EditNodeAdd: [AbsProp: test:comp, List: [Const: 123, Const: duck]], EditNodeAdd: [AbsProp: test:comp, List: [Const: 123, Const: mode]]]',
    'Query: [EditNodeAdd: [AbsProp: test:guid, Const: *], EditPropSet: [RelProp: tick, Const: 2015]]',
    'Query: [EditNodeAdd: [AbsProp: test:guid, Const: *], EditPropSet: [RelProp: tick, Const: 2016]]',
    'Query: [EditNodeAdd: [AbsProp: test:guid, Const: *], EditPropSet: [RelProp: tick, Const: 2017]]',
    'Query: [EditNodeAdd: [AbsProp: test:pivcomp, List: [Const: foo, Const: bar]], EditPropSet: [RelProp: tick, Const: 2018]]',
    'Query: [EditNodeAdd: [AbsProp: test:pivcomp, List: [Const: foo, Const: bar]]]',
    'Query: [EditNodeAdd: [AbsProp: test:pivcomp, List: [Const: hehe, Const: haha]], EditPropSet: [RelProp: tick, Const: 2015], EditTagAdd: [TagName: foo, List: [Const: 2014, Const: 2016]]]',
    'Query: [EditNodeAdd: [AbsProp: test:pivcomp, List: [Const: xxx, Const: yyy]], EditPropSet: [RelProp: width, Const: 42]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: foo bar], EditPropSet: [RelProp: tick, Const: 2018]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: bar], EditTagAdd: [TagName: baz]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: foo], EditTagAdd: [VarValue: [Const: tag]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo], FiltOper: [Const: +, TagCond: [VarValue: [Const: tag]]]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: foo], EditTagAdd: [TagName: bar], FiltOper: [Const: +, OrCond: [TagCond: [TagMatch: baz], NotCond: [HasRelPropCond: [UnivProp: .seen]]]]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: foo], EditTagAdd: [TagName: bar], FiltOper: [Const: +, NotCond: [HasRelPropCond: [UnivProp: .seen]]]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: foo], EditTagAdd: [TagName: bar], SubQuery: [Query: [EditTagAdd: [TagName: baz], FiltOper: [Const: -, TagCond: [TagMatch: bar]]]]]',
    "Query: [EditNodeAdd: [AbsProp: test:str, Const: foo], EditNodeAdd: [AbsProp: test:str, Const: bar], CmdOper: [Const: sleep, Const: ('10',)]]",
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: foo], EditNodeAdd: [AbsProp: test:str, Const: bar], CmdOper: [Const: spin, Const: ()]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: foo], EditNodeAdd: [AbsProp: test:str, Const: bar]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: foo], EditNodeAdd: [AbsProp: test:str, Const: bar], EditNodeAdd: [AbsProp: test:int, Const: 42]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: haha], EditTagAdd: [TagName: bar, Const: 2015]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: haha], EditTagAdd: [TagName: foo]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: hehe], EditTagAdd: [TagName: foo, List: [Const: 2014, Const: 2016]]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: hehe]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: oof], EditTagAdd: [TagName: bar], SubQuery: [Query: [EditNodeAdd: [AbsProp: test:int, Const: 0xdeadbeef]]]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: visi], EditTagAdd: [TagName: foo.bar], PivotToTags: [TagMatch: ], isjoin=False, EditTagAdd: [TagName: baz.faz]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: visi], EditTagAdd: [TagName: foo.bar], PivotToTags: [TagMatch: ], isjoin=False]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: visi], EditNodeAdd: [AbsProp: test:int, Const: 20], EditTagAdd: [TagName: foo.bar]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: woot], EditTagAdd: [TagName: foo, List: [Const: 2015, Const: 2018]], EditTagAdd: [TagName: bar], EditPropSet: [UnivProp: .seen, List: [Const: 2014, Const: 2016]]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: woot], EditTagAdd: [TagName: foo, List: [Const: 2015, Const: 2018]], EditPropSet: [UnivProp: .seen, List: [Const: 2014, Const: 2016]]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: woot], EditTagAdd: [TagName: foo, List: [Const: 2015, Const: 2018]]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: woot], EditPropSet: [UnivProp: .seen, List: [Const: 2014, Const: 2015]]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: woot], EditPropSet: [UnivProp: .seen, Const: 20]]',
    'Query: [EditTagDel: [TagName: foo]]',
    'Query: [EditNodeAdd: [AbsProp: edge:has, List: [List: [Const: test:str, Const: foobar], List: [Const: test:str, Const: foo]]]]',
    'Query: [EditNodeAdd: [AbsProp: edge:refs, List: [List: [Const: test:comp, List: [Const: 2048, Const: horton]], List: [Const: test:comp, List: [Const: 4096, Const: whoville]]]]]',
    'Query: [EditNodeAdd: [AbsProp: edge:refs, List: [List: [Const: test:comp, List: [Const: 9001, Const: A mean one]], List: [Const: test:comp, List: [Const: 40000, Const: greeneggs]]]]]',
    'Query: [EditNodeAdd: [AbsProp: edge:refs, List: [List: [Const: test:int, Const: 16], List: [Const: test:comp, List: [Const: 9999, Const: greenham]]]]]',
    'Query: [EditNodeAdd: [AbsProp: edge:refs, List: [List: [Const: test:str, Const: 123], List: [Const: test:int, Const: 123]]]]',
    'Query: [EditNodeAdd: [AbsProp: inet:dns:query, List: [Const: tcp://1.2.3.4, Const: , Const: 1]]]',
    'Query: [EditNodeAdd: [AbsProp: inet:dns:query, List: [Const: tcp://1.2.3.4, Const: foo*.haha.com, Const: 1]]]',
    'Query: [EditNodeAdd: [AbsProp: inet:ipv4, Const: 1.2.3.1-1.2.3.3]]',
    'Query: [EditNodeAdd: [AbsProp: inet:ipv4, Const: 1.2.3.4], EditPropSet: [RelProp: asn, Const: 10], EditNodeAdd: [AbsProp: meta:seen, List: [Const: abcd, List: [Const: inet:asn, Const: 10]]]]',
    'Query: [EditNodeAdd: [AbsProp: meta:seen, List: [Const: abcd, List: [Const: test:str, Const: pennywise]]]]',
    'Query: [EditNodeAdd: [AbsProp: meta:source, Const: abcd], EditTagAdd: [TagName: omit.nopiv], EditNodeAdd: [AbsProp: meta:seen, List: [Const: abcd, List: [Const: test:pivtarg, Const: foo]]]]',
    'Query: [EditNodeAdd: [AbsProp: test:comp, List: [Const: 1234, Const: 5678]]]',
    'Query: [EditNodeAdd: [AbsProp: test:comp, List: [Const: 3, Const: foob]], EditTagAdd: [TagName: meep.gorp], EditTagAdd: [TagName: bleep.zlorp], EditTagAdd: [TagName: cond]]',
    'Query: [EditNodeAdd: [AbsProp: test:guid, Const: *], EditPropSet: [RelProp: tick, Const: 2001]]',
    'Query: [EditNodeAdd: [AbsProp: test:guid, Const: abcd], EditPropSet: [RelProp: tick, Const: 2015]]',
    'Query: [EditNodeAdd: [AbsProp: test:int, Const: 1], EditNodeAdd: [AbsProp: test:int, Const: 2], EditNodeAdd: [AbsProp: test:int, Const: 3]]',
    'Query: [EditNodeAdd: [AbsProp: test:int, Const: 10], EditPropSet: [RelProp: loc, Const: us.va]]',
    'Query: [EditNodeAdd: [AbsProp: test:int, Const: 2], EditPropSet: [RelProp: loc, Const: us.va.sydney]]',
    'Query: [EditNodeAdd: [AbsProp: test:int, Const: 20]]',
    'Query: [EditNodeAdd: [AbsProp: test:int, Const: 3], EditPropSet: [RelProp: loc, Const: ]]',
    'Query: [EditNodeAdd: [AbsProp: test:int, Const: 4], EditPropSet: [RelProp: loc, Const: us.va.fairfax]]',
    'Query: [EditNodeAdd: [AbsProp: test:int, Const: 9], EditPropSet: [RelProp: loc, Const: us.ओं]]',
    'Query: [EditNodeAdd: [AbsProp: test:int, Const: 99999]]',
    'Query: [EditNodeAdd: [AbsProp: test:pivcomp, List: [Const: foo, Const: 123]]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: a], SwitchCase: [VarValue: [Const: woot], CaseEntry: [Const: hehe, SubQuery: [Query: [EditTagAdd: [TagName: baz]]]]]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: beep], EditNodeAdd: [AbsProp: test:str, Const: boop]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: c], SwitchCase: [VarValue: [Const: woot], CaseEntry: [Const: hehe, SubQuery: [Query: [EditTagAdd: [TagName: baz]]]], CaseEntry: [SubQuery: [Query: [EditTagAdd: [TagName: jaz]]]]]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: c], SwitchCase: [VarValue: [Const: woot], CaseEntry: [Const: hehe, SubQuery: [Query: [EditTagAdd: [TagName: baz]]]], CaseEntry: [Const: haha hoho, SubQuery: [Query: [EditTagAdd: [TagName: faz]]]], CaseEntry: [Const: lolz:lulz, SubQuery: [Query: [EditTagAdd: [TagName: jaz]]]]]]',
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: foo], EditPropSet: [RelProp: tick, Const: 201808021201]]',
    "Query: [EditNodeAdd: [AbsProp: test:str, Const: hehe], CmdOper: [Const: iden, Const: ('abcd',)], CmdOper: [Const: count, Const: ()]]",
    'Query: [EditNodeAdd: [AbsProp: test:str, Const: hello]]',
    'Query: [LiftProp: [Const: edge:refs], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: n1], Const: *range=, List: [List: [Const: test:comp, List: [Const: 1000, Const: green]], List: [Const: test:comp, List: [Const: 3000, Const: ham]]]]]]',
    'Query: [LiftProp: [Const: edge:refs]]',
    'Query: [LiftProp: [Const: edge:wentto]]',
    'Query: [LiftPropBy: [Const: file:bytes:size, Const: =, Const: 4]]',
    'Query: [ForLoop: [Const: fqdn, VarValue: [Const: fqdns], SubQuery: [Query: [EditNodeAdd: [AbsProp: inet:fqdn, VarValue: [Const: fqdn]]]]]]',
    "Query: [ForLoop: [VarList: ['fqdn', 'ipv4'], VarValue: [Const: dnsa], SubQuery: [Query: [EditNodeAdd: [AbsProp: inet:dns:a, List: [VarValue: [Const: fqdn], VarValue: [Const: ipv4]]]]]]]",
    "Query: [ForLoop: [VarList: ['fqdn', 'ipv4', 'boom'], VarValue: [Const: dnsa], SubQuery: [Query: [EditNodeAdd: [AbsProp: inet:dns:a, List: [VarValue: [Const: fqdn], VarValue: [Const: ipv4]]]]]]]",
    'Query: [LiftProp: [Const: geo:place], FiltOper: [Const: +, AbsPropCond: [AbsProp: geo:place:latlong, Const: *near=, List: [List: [Const: 34.1, Const: -118.3], Const: 10km]]]]',
    'Query: [LiftProp: [Const: geo:place], FiltOper: [Const: -, RelPropCond: [RelPropValue: [RelProp: latlong], Const: *near=, List: [List: [Const: 34.1, Const: -118.3], Const: 50m]]]]',
    'Query: [LiftPropBy: [Const: geo:place:latlong, Const: *near=, List: [List: [Const: 34.118560, Const: -118.300370], Const: 2600m]]]',
    'Query: [LiftPropBy: [Const: geo:place:latlong, Const: *near=, List: [List: [Const: 34.118560, Const: -118.300370], Const: 50m]]]',
    'Query: [LiftPropBy: [Const: geo:place:latlong, Const: *near=, List: [List: [Const: 0, Const: 0], Const: 50m]]]',
    'Query: [LiftPropBy: [Const: geo:place:latlong, Const: *near=, List: [List: [Const: 34.1, Const: -118.3], Const: 10km]]]',
    'Query: [LiftPropBy: [Const: geo:place, Const: =, VarValue: [Const: place]], PivotInFrom: [AbsProp: edge:has], isjoin=False, PivotIn: [], isjoin=False]',
    'Query: [LiftPropBy: [Const: geo:place, Const: =, VarValue: [Const: place]], PivotInFrom: [AbsProp: edge:has], isjoin=False, PivotInFrom: [AbsProp: ps:person], isjoin=False]',
    'Query: [LiftPropBy: [Const: geo:place, Const: =, Const: abcd], VarSetOper: [Const: latlong, RelPropValue: [RelProp: latlong]], VarSetOper: [Const: radius, RelPropValue: [RelProp: radius]], CmdOper: [Const: spin, Const: ()], LiftPropBy: [Const: tel:mob:telem:latlong, Const: *near=, List: [VarValue: [Const: latlong], Const: 3km]]]',
    "Query: [LiftPropBy: [Const: graph:cluster, Const: =, Const: abcd], CmdOper: [Const: noderefs, Const: ('-d', '2', '--join')]]",
    'Query: [CmdOper: [Const: help, Const: ()]]',
    "Query: [CmdOper: [Const: iden, Const: ('2cdd997872b10a65407ad5fadfa28e0d',)]]",
    "Query: [CmdOper: [Const: iden, Const: ('deadb33f',)]]",
    "Query: [VarSetOper: [Const: foo, Const: 42], CmdOper: [Const: iden, Const: ('deadb33f',)]]",
    "Query: [LiftPropBy: [Const: inet:asn, Const: =, Const: 10], CmdOper: [Const: noderefs, Const: ('-of', 'inet:ipv4', '--join', '-d', '3')]]",
    'Query: [LiftProp: [Const: inet:dns:a], FiltOper: [Const: +, SubqCond: [Query: [PropPivot: [RelPropValue: [RelProp: ipv4], AbsProp: inet:ipv4], isjoin=False, FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: loc], Const: =, Const: us]]]]]]',
    'Query: [LiftProp: [Const: inet:dns:a], FiltOper: [Const: +, SubqCond: [Query: [PropPivot: [RelPropValue: [RelProp: ipv4], AbsProp: inet:ipv4], isjoin=False, FiltOper: [Const: -, RelPropCond: [RelPropValue: [RelProp: loc], Const: =, Const: us]]]]]]',
    'Query: [LiftProp: [Const: inet:dns:a], FiltOper: [Const: -, SubqCond: [Query: [PropPivot: [RelPropValue: [RelProp: ipv4], AbsProp: inet:ipv4], isjoin=False, FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: loc], Const: =, Const: us]]]]]]',
    'Query: [LiftProp: [Const: inet:dns:a], FiltOper: [Const: -, SubqCond: [Query: [PropPivot: [RelPropValue: [RelProp: ipv4], AbsProp: inet:ipv4], isjoin=False, FiltOper: [Const: -, RelPropCond: [RelPropValue: [RelProp: loc], Const: =, Const: us]]]]]]',
    'Query: [LiftProp: [Const: inet:dns:a], PropPivotOut: [RelProp: ipv4], isjoin=False]',
    'Query: [LiftPropBy: [Const: inet:dns:a, Const: =, List: [Const: woot.com, Const: 12.34.56.78]], EditPropSet: [UnivProp: .seen, List: [Const: 201708010123, Const: 201708100456]]]',
    'Query: [LiftPropBy: [Const: inet:dns:a, Const: =, List: [Const: woot.com, Const: 12.34.56.78]], EditPropSet: [UnivProp: .seen, List: [Const: 201708010123, Const: ?]]]',
    'Query: [LiftProp: [Const: inet:dns:a]]',
    'Query: [LiftPropBy: [Const: inet:dns:a, Const: =, List: [Const: woot.com, Const: 1.2.3.4]], VarSetOper: [Const: hehe, RelPropValue: [RelProp: fqdn]], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: fqdn], Const: =, VarValue: [Const: hehe]]]]',
    'Query: [LiftPropBy: [Const: inet:dns:a, Const: =, List: [Const: woot.com, Const: 1.2.3.4]], VarSetOper: [Const: hehe, RelPropValue: [RelProp: fqdn]], FiltOper: [Const: -, RelPropCond: [RelPropValue: [RelProp: fqdn], Const: =, VarValue: [Const: hehe]]]]',
    'Query: [LiftPropBy: [Const: inet:dns:a, Const: =, List: [Const: woot.com, Const: 1.2.3.4]], VarSetOper: [Const: hehe, RelPropValue: [RelProp: fqdn]], LiftPropBy: [Const: inet:fqdn, Const: =, VarValue: [Const: hehe]]]',
    'Query: [LiftPropBy: [Const: inet:dns:a, Const: =, List: [Const: woot.com, Const: 1.2.3.4]], VarSetOper: [Const: newp, UnivPropValue: [UnivProp: .seen]]]',
    'Query: [LiftPropBy: [Const: inet:dns:a, Const: =, List: [Const: woot.com, Const: 1.2.3.4]], VarSetOper: [Const: seen, UnivPropValue: [UnivProp: .seen]], PropPivot: [RelPropValue: [RelProp: fqdn], AbsProp: inet:fqdn], isjoin=False, EditPropSet: [UnivProp: .seen, VarValue: [Const: seen]]]',
    'Query: [LiftPropBy: [Const: inet:dns:a, Const: =, List: [Const: woot.com, Const: 1.2.3.4]], EditPropSet: [UnivProp: .seen, List: [Const: 2015, Const: 2018]]]',
    'Query: [LiftPropBy: [Const: inet:dns:query, Const: =, List: [Const: tcp://1.2.3.4, Const: , Const: 1]], PropPivot: [RelPropValue: [RelProp: name], AbsProp: inet:fqdn], isjoin=False]',
    'Query: [LiftPropBy: [Const: inet:dns:query, Const: =, List: [Const: tcp://1.2.3.4, Const: foo*.haha.com, Const: 1]], PropPivot: [RelPropValue: [RelProp: name], AbsProp: inet:fqdn], isjoin=False]',
    'Query: [LiftProp: [Const: inet:fqdn], FiltOper: [Const: +, TagCond: [TagMatch: bad]], VarSetOper: [Const: fqdnbad, TagPropValue: [TagName: bad]], FormPivot: [AbsProp: inet:dns:a:fqdn], isjoin=False, FiltOper: [Const: +, RelPropCond: [RelPropValue: [UnivProp: .seen], Const: @=, VarValue: [Const: fqdnbad]]]]',
    'Query: [LiftPropBy: [Const: inet:fqdn, Const: =, Const: woot.com], FormPivot: [AbsProp: inet:dns:a], isjoin=False, FormPivot: [AbsProp: inet:ipv4], isjoin=False]',
    'Query: [LiftPropBy: [Const: inet:fqdn, Const: =, Const: woot.com], FormPivot: [AbsProp: inet:dns:a], isjoin=False]',
    'Query: [LiftPropBy: [Const: inet:fqdn, Const: =, Const: woot.com], CmdOper: [Const: delnode, Const: ()]]',
    "Query: [LiftProp: [Const: inet:fqdn], CmdOper: [Const: graph, Const: ('--filter', '{ -#nope }')]]",
    'Query: [LiftPropBy: [Const: inet:fqdn, Const: =, Const: woot.com]]',
    'Query: [LiftProp: [Const: inet:ipv4], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: asn::name], Const: =, Const: visi]]]',
    'Query: [LiftProp: [Const: inet:ipv4], FiltOper: [Const: +, AbsPropCond: [AbsProp: inet:ipv4, Const: =, Const: 1.2.3.0/30]]]',
    'Query: [LiftProp: [Const: inet:ipv4], FiltOper: [Const: +, AbsPropCond: [AbsProp: inet:ipv4, Const: =, Const: 1.2.3.1-1.2.3.3]]]',
    'Query: [LiftProp: [Const: inet:ipv4], FiltOper: [Const: +, AbsPropCond: [AbsProp: inet:ipv4, Const: =, Const: 10.2.1.4/32]]]',
    'Query: [LiftProp: [Const: inet:ipv4], FormPivot: [AbsProp: test:str], isjoin=False]',
    "Query: [LiftProp: [Const: inet:ipv4], CmdOper: [Const: reindex, Const: ('--subs',)]]",
    'Query: [LiftPropBy: [Const: inet:ipv4:loc, Const: =, Const: us]]',
    'Query: [LiftPropBy: [Const: inet:ipv4:loc, Const: =, Const: zz]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.1-1.2.3.3]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 192.168.1.0/24]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.4], FiltOper: [Const: +, HasRelPropCond: [RelProp: asn]]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.4], FiltOper: [Const: +, SubqCond: [Query: [FormPivot: [AbsProp: inet:dns:a], isjoin=False], Const: <, Const: 2]]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.4], FiltOper: [Const: +, SubqCond: [Query: [FormPivot: [AbsProp: inet:dns:a], isjoin=False], Const: <=, Const: 1]]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.4], FiltOper: [Const: +, SubqCond: [Query: [FormPivot: [AbsProp: inet:dns:a], isjoin=False], Const: !=, Const: 2]]]',
    "Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1.2.3.4], CmdOper: [Const: limit, Const: ('20',)]]",
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 12.34.56.78], EditPropSet: [RelProp: loc, Const: us.oh.wilmington]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 12.34.56.78], LiftPropBy: [Const: inet:fqdn, Const: =, Const: woot.com], EditNodeAdd: [AbsProp: inet:ipv4, Const: 1.2.3.4], EditPropSet: [RelProp: asn, Const: 10101], EditNodeAdd: [AbsProp: inet:fqdn, Const: woowoo.com], EditTagAdd: [TagName: my.tag]]',
    "Query: [LiftProp: [Const: inet:user], CmdOper: [Const: limit, Const: ('--woot',)]]",
    "Query: [LiftProp: [Const: inet:user], CmdOper: [Const: limit, Const: ('1',)]]",
    "Query: [LiftProp: [Const: inet:user], CmdOper: [Const: limit, Const: ('10',)], FiltOper: [Const: +, AbsPropCond: [AbsProp: inet:user, Const: =, Const: visi]]]",
    "Query: [LiftProp: [Const: inet:user], CmdOper: [Const: limit, Const: ('10',)], EditTagAdd: [TagName: foo.bar]]",
    'Query: [LiftPropBy: [Const: media:news, Const: =, Const: 00a1f0d928e25729b9e86e2d08c127ce], EditPropSet: [RelProp: summary, Const: ]]',
    'Query: [LiftPropBy: [Const: meta:seen:meta:source, Const: =, VarValue: [Const: sorc]], PivotOut: [], isjoin=False]',
    'Query: [LiftPropBy: [Const: meta:seen:meta:source, Const: =, VarValue: [Const: sorc]], PropPivotOut: [RelProp: node], isjoin=False]',
    'Query: [LiftPropBy: [Const: meta:source, Const: =, Const: 8f1401de15918358d5247e21ca29a814]]',
    "Query: [CmdOper: [Const: movetag, Const: ('#a.b', '#a.m')]]",
    "Query: [CmdOper: [Const: movetag, Const: ('#hehe', '#woot')]]",
    'Query: [LiftPropBy: [Const: ps:person, Const: =, VarValue: [Const: pers]], FormPivot: [AbsProp: edge:has], isjoin=False, PivotOut: [], isjoin=False]',
    'Query: [LiftPropBy: [Const: ps:person, Const: =, VarValue: [Const: pers]], FormPivot: [AbsProp: edge:has], isjoin=False, FormPivot: [AbsProp: geo:place], isjoin=False]',
    'Query: [LiftPropBy: [Const: ps:person, Const: =, VarValue: [Const: pers]], FormPivot: [AbsProp: edge:wentto], isjoin=False, FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: time], Const: @=, List: [Const: 2014, Const: 2017]]], FormPivot: [AbsProp: geo:place], isjoin=False]',
    'Query: [LiftPropBy: [Const: ps:person, Const: =, VarValue: [Const: pers]], FormPivot: [AbsProp: edge:wentto], isjoin=False, PivotOut: [], isjoin=False]',
    'Query: [LiftPropBy: [Const: ps:person, Const: =, VarValue: [Const: pers]], FormPivot: [AbsProp: edge:wentto], isjoin=False, PropPivotOut: [RelProp: n2], isjoin=False]',
    "Query: [CmdOper: [Const: reindex, Const: ('--form-counts',)]]",
    'Query: [CmdOper: [Const: sudo, Const: ()], EditNodeAdd: [AbsProp: inet:ipv4, Const: 1.2.3.4]]',
    'Query: [CmdOper: [Const: sudo, Const: ()], EditNodeAdd: [AbsProp: test:cycle0, Const: foo], EditPropSet: [RelProp: test:cycle1, Const: bar]]',
    'Query: [CmdOper: [Const: sudo, Const: ()], EditNodeAdd: [AbsProp: test:guid, Const: *]]',
    'Query: [CmdOper: [Const: sudo, Const: ()], EditNodeAdd: [AbsProp: test:str, Const: foo], EditTagAdd: [TagName: lol]]',
    'Query: [CmdOper: [Const: sudo, Const: ()], EditNodeAdd: [AbsProp: test:str, Const: foo]]',
    'Query: [CmdOper: [Const: sudo, Const: ()], EditNodeAdd: [AbsProp: test:str, Const: 123], EditPropSet: [RelProp: tick, Const: 2018]]',
    'Query: [CmdOper: [Const: sudo, Const: ()], LiftPropBy: [Const: test:int, Const: =, Const: 6], CmdOper: [Const: delnode, Const: ()]]',
    'Query: [LiftPropBy: [Const: syn:tag, Const: =, Const: a.b], FiltOper: [Const: +, TagCond: [TagMatch: foo]]]',
    'Query: [LiftPropBy: [Const: syn:tag, Const: =, Const: aaa.barbarella.ddd]]',
    'Query: [LiftPropBy: [Const: syn:tag, Const: =, Const: baz.faz], EditTagAdd: [TagName: foo.bar]]',
    'Query: [LiftPropBy: [Const: syn:tag, Const: =, Const: foo.bar], PivotOut: [], isjoin=False]',
    'Query: [LiftPropBy: [Const: syn:tag, Const: =, Const: foo.bar], FormPivot: [AbsProp: test:str], isjoin=False]',
    'Query: [LiftPropBy: [Const: syn:tag, Const: =, Const: foo.bar], FormPivot: [AbsProp: test:str:tick], isjoin=False]',
    'Query: [LiftProp: [Const: test:comp], FiltOper: [Const: +, AndCond: [RelPropCond: [RelPropValue: [RelProp: hehe], Const: <, Const: 2], RelPropCond: [RelPropValue: [RelProp: haha], Const: =, Const: test]]]]',
    'Query: [LiftProp: [Const: test:comp], FiltOper: [Const: +, OrCond: [RelPropCond: [RelPropValue: [RelProp: hehe], Const: <, Const: 2], TagCond: [TagMatch: meep.gorp]]]]',
    'Query: [LiftProp: [Const: test:comp], FiltOper: [Const: +, OrCond: [RelPropCond: [RelPropValue: [RelProp: hehe], Const: <, Const: 2], RelPropCond: [RelPropValue: [RelProp: haha], Const: =, Const: test]]]]',
    'Query: [LiftProp: [Const: test:comp], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: haha], Const: *range=, List: [Const: grinch, Const: meanone]]]]',
    'Query: [LiftProp: [Const: test:comp], FiltOper: [Const: +, AbsPropCond: [AbsProp: test:comp, Const: *range=, List: [List: [Const: 1024, Const: grinch], List: [Const: 4096, Const: zemeanone]]]]]',
    'Query: [LiftProp: [Const: test:comp], PivotOut: [], isjoin=False, CmdOper: [Const: uniq, Const: ()], CmdOper: [Const: count, Const: ()]]',
    'Query: [LiftProp: [Const: test:comp], PivotOut: [], isjoin=False]',
    'Query: [LiftProp: [Const: test:comp], FormPivot: [AbsProp: test:int], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:comp:haha, Const: ~=, Const: ^lulz]]',
    'Query: [LiftPropBy: [Const: test:comp:haha, Const: ~=, Const: ^zerg]]',
    'Query: [LiftFormTag: [Const: test:comp, TagName: bar], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: hehe], Const: =, Const: 1010]], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: haha], Const: =, Const: test10]], FiltOper: [Const: +, TagCond: [TagMatch: bar]]]',
    'Query: [LiftProp: [Const: test:guid], FiltOper: [Const: +, AbsPropCond: [AbsProp: test:guid, Const: *range=, List: [Const: abcd, Const: dcbe]]]]',
    "Query: [LiftProp: [Const: test:guid], CmdOper: [Const: max, Const: ('tick',)]]",
    "Query: [LiftProp: [Const: test:guid], CmdOper: [Const: min, Const: ('tick',)]]",
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: loc], Const: =, Const: ]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: loc], Const: =, Const: us.va. syria]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: loc], Const: =, Const: u]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: loc], Const: =, Const: us]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: loc], Const: =, Const: us.v]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: loc], Const: =, Const: us.va.sydney]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: loc], Const: ^=, Const: ]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: loc], Const: ^=, Const: 23]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: loc], Const: ^=, Const: u]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: loc], Const: ^=, Const: us]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: loc], Const: ^=, Const: us.]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: loc], Const: ^=, Const: us.va.]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: loc], Const: ^=, Const: us.va.fairfax.reston]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, AbsPropCond: [AbsProp: test:int, Const: <, Const: 30]]]',
    'Query: [LiftProp: [Const: test:int], FiltOper: [Const: +, AbsPropCond: [AbsProp: test:int, Const: <=, Const: 30]]]',
    'Query: [LiftPropBy: [Const: test:int, Const: <=, Const: 20]]',
    'Query: [LiftProp: [Const: test:int], CmdOper: [Const: noderefs, Const: ()], FiltOper: [Const: +, AbsPropCond: [AbsProp: test:comp, Const: *range=, List: [List: [Const: 1000, Const: grinch], List: [Const: 4000, Const: whoville]]]]]',
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
    "Query: [LiftPropBy: [Const: test:int, Const: =, Const: 123], CmdOper: [Const: noderefs, Const: ('-te',)]]",
    'Query: [LiftPropBy: [Const: test:int, Const: =, Const: 123], CmdOper: [Const: noderefs, Const: ()]]',
    'Query: [LiftPropBy: [Const: test:int, Const: =, Const: 1234], EditNodeAdd: [AbsProp: test:str, FuncCall: [VarDeref: [VarValue: [Const: node], Const: form], CallArgs: [], CallKwargs: []]], FiltOper: [Const: -, HasAbsPropCond: [AbsProp: test:int]]]',
    'Query: [LiftPropBy: [Const: test:int, Const: =, Const: 1234], EditNodeAdd: [AbsProp: test:str, FuncCall: [VarDeref: [VarValue: [Const: node], Const: value], CallArgs: [], CallKwargs: []]], FiltOper: [Const: -, HasAbsPropCond: [AbsProp: test:int]]]',
    'Query: [LiftPropBy: [Const: test:int, Const: =, Const: 3735928559]]',
    'Query: [LiftPropBy: [Const: test:int, Const: =, Const: 8675309]]',
    'Query: [LiftPropBy: [Const: test:int, Const: >, Const: 30]]',
    'Query: [LiftPropBy: [Const: test:int, Const: >=, Const: 20]]',
    'Query: [LiftProp: [Const: test:pivcomp], FormPivot: [AbsProp: test:int], isjoin=False]',
    "Query: [LiftProp: [Const: test:pivcomp], CmdOper: [Const: noderefs, Const: ('--join', '--degrees', '2')]]",
    "Query: [LiftProp: [Const: test:pivcomp], CmdOper: [Const: noderefs, Const: ('--join', '-d', '3')]]",
    "Query: [LiftProp: [Const: test:pivcomp], CmdOper: [Const: noderefs, Const: ('--join',)]]",
    "Query: [LiftProp: [Const: test:pivcomp], CmdOper: [Const: noderefs, Const: ('-j', '--degrees', '2')]]",
    'Query: [LiftProp: [Const: test:pivcomp], CmdOper: [Const: noderefs, Const: ()]]',
    'Query: [LiftPropBy: [Const: test:pivcomp:tick, Const: =, VarValue: [Const: foo]]]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, VarValue: [Const: foo]]]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], FiltOper: [Const: +, SubqCond: [Query: [PropPivot: [RelPropValue: [RelProp: lulz], AbsProp: test:str], isjoin=False, FiltOper: [Const: +, TagCond: [TagMatch: baz]]]]], FiltOper: [Const: +, HasAbsPropCond: [AbsProp: test:pivcomp]]]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], PivotOut: [], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], FormPivot: [AbsProp: test:pivtarg], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], PivotOut: [], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], FormPivot: [AbsProp: test:pivtarg], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], FiltOper: [Const: -, SubqCond: [Query: [PropPivot: [RelPropValue: [RelProp: lulz], AbsProp: test:str], isjoin=False, FiltOper: [Const: +, TagCond: [TagMatch: baz]]]]]]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], PropPivot: [RelPropValue: [RelProp: lulz], AbsProp: test:str], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], PropPivot: [RelPropValue: [RelProp: lulz], AbsProp: test:str], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], PropPivot: [RelPropValue: [RelProp: targ], AbsProp: test:pivtarg], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: hehe, Const: haha]], VarSetOper: [Const: ticktock, TagPropValue: [TagName: foo]], FormPivot: [AbsProp: test:pivtarg], isjoin=False, FiltOper: [Const: +, RelPropCond: [RelPropValue: [UnivProp: .seen], Const: @=, VarValue: [Const: ticktock]]]]',
    'Query: [LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: hehe, Const: haha]]]',
    'Query: [LiftPropBy: [Const: test:pivtarg, Const: =, Const: hehe], EditPropSet: [UnivProp: .seen, Const: 2015]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, TagCond: [TagMatch: *]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, TagCond: [TagMatch: **.bar.baz]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, TagCond: [TagMatch: **.baz]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, TagCond: [TagMatch: *.bad]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, TagCond: [TagMatch: foo.**.baz]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, TagCond: [TagMatch: foo.*.baz]]]',
    'Query: [LiftTag: [TagName: foo, Const: @=, List: [Const: 2013, Const: 2015]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, TagValuCond: [TagMatch: foo, Const: @=, List: [Const: 2014, Const: 20141231]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, TagValuCond: [TagMatch: foo, Const: @=, List: [Const: 2015, Const: 2018]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, TagValuCond: [TagMatch: foo, Const: @=, Const: 2016]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: .seen], Const: *range=, List: [List: [Const: 20090601, Const: 20090701], List: [Const: 20110905, Const: 20110906]]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: bar], Const: *range=, List: [List: [Const: test:str, Const: c], List: [Const: test:str, Const: q]]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: tick], Const: *range=, List: [Const: 19701125, Const: 20151212]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: tick], Const: =, List: [VarValue: [Const: test], Const: +- 2day]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: tick], Const: =, List: [Const: 2015, Const: +1 day]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: tick], Const: =, List: [Const: 20150102, Const: -3 day]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: tick], Const: =, List: [Const: 20150201, Const: +1 day]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: tick], Const: =, Const: 2015]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: tick], Const: @=, List: [Const: -1 day]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: tick], Const: @=, List: [Const: now+2days, Const: -3 day]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: tick], Const: @=, List: [Const: now-1day, Const: ?]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: tick], Const: @=, List: [Const: 2015]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: tick], Const: @=, List: [Const: 2015, Const: +1 day]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: tick], Const: @=, List: [Const: 20150102+1day, Const: -4 day]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: tick], Const: @=, List: [Const: 20150102, Const: -4 day]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: tick], Const: @=, List: [Const: now, Const: -1 day]]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, AbsPropCond: [AbsProp: test:str:tick, Const: <, Const: 201808021202]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, AbsPropCond: [AbsProp: test:str:tick, Const: <=, Const: 201808021202]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, AbsPropCond: [AbsProp: test:str:tick, Const: >, Const: 201808021202]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: +, AbsPropCond: [AbsProp: test:str:tick, Const: >=, Const: 201808021202]]]',
    'Query: [LiftProp: [Const: test:str], FiltOper: [Const: -, TagCond: [TagMatch: *]]]',
    'Query: [LiftProp: [Const: test:str], EditTagAdd: [TagName: foo.bar, List: [Const: 2000, Const: 2002]]]',
    'Query: [LiftProp: [Const: test:str], EditTagAdd: [TagName: foo.bar, List: [Const: 2000, Const: 20020601]]]',
    'Query: [LiftProp: [Const: test:str], EditTagAdd: [TagName: foo.bar]]',
    'Query: [LiftProp: [Const: test:str], EditTagDel: [TagName: foo]]',
    'Query: [LiftProp: [Const: test:str], EditPropDel: [RelProp: tick]]',
    "Query: [LiftProp: [Const: test:str], CmdOper: [Const: delnode, Const: ('--force',)]]",
    "Query: [LiftProp: [Const: test:str], CmdOper: [Const: noderefs, Const: ('-d', '3', '--unique')]]",
    "Query: [LiftProp: [Const: test:str], CmdOper: [Const: noderefs, Const: ('-d', '3')]]",
    'Query: [LiftFormTag: [Const: test:str, TagName: foo]]',
    'Query: [LiftFormTag: [Const: test:str, TagName: foo.bar]]',
    'Query: [LiftFormTag: [Const: test:str, TagName: foo, Const: @=, List: [Const: 2012, Const: 2022]]]',
    'Query: [LiftFormTag: [Const: test:str, TagName: foo, Const: @=, Const: 2016]]',
    'Query: [LiftProp: [Const: test:str]]',
    'Query: [LiftPropBy: [Const: test:str:tick, Const: <, Const: 201808021202]]',
    'Query: [LiftPropBy: [Const: test:str:tick, Const: <=, Const: 201808021202]]',
    'Query: [LiftPropBy: [Const: test:str:tick, Const: =, List: [Const: 20131231, Const: +2 days]]]',
    'Query: [LiftPropBy: [Const: test:str:tick, Const: =, Const: 2015]]',
    'Query: [LiftPropBy: [Const: test:str:tick, Const: >, Const: 201808021202]]',
    'Query: [LiftPropBy: [Const: test:str:tick, Const: >=, Const: 201808021202]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo bar], FiltOper: [Const: +, HasAbsPropCond: [AbsProp: test:str]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo bar], FiltOper: [Const: -, HasAbsPropCond: [AbsProp: test:str:tick]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo bar], EditPropDel: [RelProp: tick]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, VarValue: [Const: foo]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: 123], EditPropSet: [RelProp: baz, Const: test:guid:tick=2015]]',
    "Query: [LiftPropBy: [Const: test:str, Const: =, Const: 123], CmdOper: [Const: noderefs, Const: ('--traverse-edge',)]]",
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: 123], CmdOper: [Const: noderefs, Const: ()]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: 1234], LiftPropBy: [Const: test:str, Const: =, Const: duck], LiftPropBy: [Const: test:str, Const: =, Const: knight]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: a], FiltOper: [Const: +, RelPropCond: [RelPropValue: [RelProp: tick], Const: *range=, List: [Const: 20000101, Const: 20101201]]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: bar], FormPivot: [AbsProp: test:pivcomp:lulz], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: bar], FormPivot: [AbsProp: test:pivcomp:lulz], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: bar], PivotIn: [], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: bar], PivotIn: [], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: bar], LiftPropBy: [Const: test:pivcomp, Const: =, List: [Const: foo, Const: bar]], EditTagAdd: [TagName: test.bar]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo], FiltOper: [Const: +, TagValuCond: [TagMatch: lol, Const: @=, Const: 2016]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo], PivotInFrom: [AbsProp: edge:has], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo], PivotInFrom: [AbsProp: edge:has], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foo], CmdOper: [Const: delnode, Const: ()]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foobar], FormPivot: [AbsProp: edge:has], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foobar], FormPivot: [AbsProp: edge:has], isjoin=False, PivotInFrom: [AbsProp: test:str], isjoin=True]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: foobar], FormPivot: [AbsProp: edge:has], isjoin=False, PivotInFrom: [AbsProp: test:str], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: hello], EditPropSet: [RelProp: tick, Const: 2001]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: hello], EditPropSet: [RelProp: tick, Const: 2002]]',
    "Query: [LiftPropBy: [Const: test:str, Const: =, Const: pennywise], CmdOper: [Const: noderefs, Const: ('--join', '-d', '9', '--traverse-edge')]]",
    "Query: [LiftPropBy: [Const: test:str, Const: =, Const: pennywise], CmdOper: [Const: noderefs, Const: ('-d', '3', '--omit-traversal-tag=omit.nopiv', '--omit-traversal-tag=test')]]",
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: visi], PivotToTags: [TagMatch: *], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: visi], PivotToTags: [TagMatch: foo.*], isjoin=False]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: woot], VarSetOper: [Const: foo, TagPropValue: [TagName: foo]], FiltOper: [Const: +, RelPropCond: [RelPropValue: [UnivProp: .seen], Const: @=, VarValue: [Const: foo]]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: woot], FiltOper: [Const: +, RelPropCond: [RelPropValue: [UnivProp: .seen], Const: @=, TagPropValue: [TagName: bar]]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: woot], FiltOper: [Const: +, RelPropCond: [RelPropValue: [UnivProp: .seen], Const: @=, List: [Const: 2012, Const: 2015]]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: =, Const: woot], FiltOper: [Const: +, RelPropCond: [RelPropValue: [UnivProp: .seen], Const: @=, Const: 2012]]]',
    'Query: [LiftPropBy: [Const: test:str, Const: ~=, Const: zip]]',
    "Query: [ForLoop: [Const: foo, VarValue: [Const: foos], SubQuery: [Query: [VarListSetOper: [VarList: ['fqdn', 'ipv4'], FuncCall: [VarDeref: [VarValue: [Const: foo], Const: split], CallArgs: [Const: |], CallKwargs: []]], EditNodeAdd: [AbsProp: inet:dns:a, List: [VarValue: [Const: fqdn], VarValue: [Const: ipv4]]]]]]]",
    'Query: [LiftProp: [Const: test:int]]',
    'Query: [LiftProp: [Const: test:int]]',
    'Query: [LiftProp: [Const: test:int]]',
    'Query: [EditNodeAdd: [AbsProp: inet:ipv4, Const: 1.2.3.4], SwitchCase: [VarValue: [Const: foo], CaseEntry: [Const: bar, SubQuery: [Query: [EditTagAdd: [TagName: hehe.haha]]]], CaseEntry: [Const: baz faz, SubQuery: [Query: []]]]]',
    "Query: [LiftProp: [Const: inet:fqdn], CmdOper: [Const: graph, Const: ('--degrees', '2', '--filter', '{ -#nope }', '--pivot', '{ <- meta:seen <- meta:source }', '--form-pivot', 'inet:fqdn', '{<- * | limit 20}', '--form-pivot', 'inet:fqdn', '{-> * | limit 20}', '--form-filter', 'inet:fqdn', '{-inet:fqdn:issuffix=1}', '--form-pivot', 'syn:tag', '{-> *}', '--form-pivot', '*', '{-> #}')]]",
    'Query: [ForLoop: [Const: foo, VarValue: [Const: foos], SubQuery: [Query: [EditNodeAdd: [AbsProp: inet:ipv4, Const: 1.2.3.4], SwitchCase: [VarValue: [Const: foo], CaseEntry: [Const: bar, SubQuery: [Query: [EditTagAdd: [TagName: ohai], BreakOper: []]]], CaseEntry: [Const: baz, SubQuery: [Query: [EditTagAdd: [TagName: visi], ContinueOper: []]]]], EditNodeAdd: [AbsProp: inet:ipv4, Const: 5.6.7.8], EditTagAdd: [TagName: hehe]]]]]',
    "Query: [ForLoop: [Const: foo, VarValue: [Const: foos], SubQuery: [Query: [VarListSetOper: [VarList: ['fqdn', 'ipv4'], FuncCall: [VarDeref: [VarValue: [Const: foo], Const: split], CallArgs: [Const: |], CallKwargs: []]], EditNodeAdd: [AbsProp: inet:dns:a, List: [VarValue: [Const: fqdn], VarValue: [Const: ipv4]]]]]]]",
    'Query: [ForLoop: [Const: tag, FuncCall: [VarDeref: [VarValue: [Const: node], Const: tags], CallArgs: [], CallKwargs: []], SubQuery: [Query: [FormPivot: [AbsProp: test:int], isjoin=False, EditTagAdd: [VarValue: [Const: tag]]]]]]',
    'Query: [ForLoop: [Const: tag, FuncCall: [VarDeref: [VarValue: [Const: node], Const: tags], CallArgs: [Const: fo*], CallKwargs: []], SubQuery: [Query: [FormPivot: [AbsProp: test:int], isjoin=False, EditTagDel: [VarValue: [Const: tag]]]]]]',
    'Query: [EditNodeAdd: [AbsProp: inet:email:message, Const: *], EditPropSet: [RelProp: to, Const: woot@woot.com], EditPropSet: [RelProp: from, Const: visi@vertex.link], EditPropSet: [RelProp: replyto, Const: root@root.com], EditPropSet: [RelProp: subject, Const: hi there], EditPropSet: [RelProp: date, Const: 2015], EditPropSet: [RelProp: body, Const: there are mad sploitz here!], EditPropSet: [RelProp: bytes, Const: *], SubQuery: [Query: [EditNodeAdd: [AbsProp: inet:email:message:link, List: [VarValue: [Const: node], Const: https://www.vertex.link]]]], SubQuery: [Query: [EditNodeAdd: [AbsProp: inet:email:message:attachment, List: [VarValue: [Const: node], Const: *]], FiltOper: [Const: -, HasAbsPropCond: [AbsProp: inet:email:message]], EditPropSet: [RelProp: name, Const: sploit.exe]]], SubQuery: [Query: [EditNodeAdd: [AbsProp: edge:has, List: [VarValue: [Const: node], List: [Const: inet:email:header, List: [Const: to, Const: Visi Kensho <visi@vertex.link>]]]]]]]',
    'Query: [VarSetOper: [Const: x, DollarExpr: [ExprNode: [Const: 1, Const: /, Const: 3]]]]',
    'Query: [VarSetOper: [Const: x, DollarExpr: [ExprNode: [Const: 1, Const: *, Const: 3]]]]',
    'Query: [VarSetOper: [Const: x, DollarExpr: [ExprNode: [ExprNode: [Const: 1, Const: *, Const: 3], Const: +, Const: 2]]]]',
    'Query: [VarSetOper: [Const: x, DollarExpr: [ExprNode: [Const: 1, Const: -, ExprNode: [Const: 3.2, Const: /, Const: -3.2]]]]]',
    'Query: [VarSetOper: [Const: x, DollarExpr: [ExprNode: [Const: 1, Const: +, ExprNode: [Const: 3, Const: /, Const: 2]]]]]',
    'Query: [VarSetOper: [Const: x, DollarExpr: [ExprNode: [ExprNode: [Const: 1, Const: +, Const: 3], Const: /, Const: 2]]]]',
    'Query: [VarSetOper: [Const: foo, Const: 42], VarSetOper: [Const: foo2, Const: 43], VarSetOper: [Const: x, DollarExpr: [ExprNode: [VarValue: [Const: foo], Const: *, VarValue: [Const: foo2]]]]]',
    'Query: [VarSetOper: [Const: yep, DollarExpr: [ExprNode: [Const: 42, Const: <, Const: 43]]]]',
    'Query: [VarSetOper: [Const: yep, DollarExpr: [ExprNode: [Const: 42, Const: >, Const: 43]]]]',
    'Query: [VarSetOper: [Const: yep, DollarExpr: [ExprNode: [Const: 42, Const: >=, Const: 43]]]]',
    'Query: [VarSetOper: [Const: yep, DollarExpr: [ExprNode: [ExprNode: [Const: 42, Const: +, Const: 4], Const: <=, ExprNode: [Const: 43, Const: *, Const: 43]]]]]',
    'Query: [VarSetOper: [Const: foo, Const: 4.3], VarSetOper: [Const: bar, Const: 4.2], VarSetOper: [Const: baz, DollarExpr: [ExprNode: [VarValue: [Const: foo], Const: +, VarValue: [Const: bar]]]]]',
    'Query: [LiftPropBy: [Const: inet:ipv4, Const: =, Const: 1], VarSetOper: [Const: foo, UnivPropValue: [UnivProp: .created]], VarSetOper: [Const: bar, DollarExpr: [ExprNode: [VarValue: [Const: foo], Const: +, Const: 1]]]]',
    'Query: [VarSetOper: [Const: x, DollarExpr: [FuncCall: [VarDeref: [VarDeref: [VarValue: [Const: lib], Const: time], Const: offset], CallArgs: [Const: 2 days], CallKwargs: []]]]]',
    'Query: [VarSetOper: [Const: foo, Const: 1], VarSetOper: [Const: bar, Const: 2], LiftPropBy: [Const: inet:ipv4, Const: =, DollarExpr: [ExprNode: [VarValue: [Const: foo], Const: +, VarValue: [Const: bar]]]]]',
    'Query: []',
    "Query: [CmdOper: [Const: hehe.haha, Const: ('--size', '10', '--query', 'foo_bar.stuff:baz')]]",
]

class GrammarTest(s_t_utils.SynTest):

    @unittest.skip('Strict subset of test_parser.  Only useful for debugging grammar')
    def test_grammar(self):
        with s_datfile.openDatFile('synapse.lib/storm.lark') as larkf:
            grammar = larkf.read().decode()

        parser = lark.Lark(grammar, start='query', debug=True)

        for i, query in enumerate(_Queries):
            try:
                tree = parser.parse(query)
                # print(f'#{i}: {query}')
                # print(tree.pretty(), '\n')
            except (lark.ParseError, lark.UnexpectedCharacters):
                print(f'Failure on parsing #{i}:\n{{{query}}}')
                raise

    async def test_parser(self):
        self.maxDiff = None
        for i, query in enumerate(_Queries):
            parser = s_grammar.Parser(query)
            tree = parser.query()

            self.eq(str(tree), _ParseResults[i])

    def test_stormcmdargs(self):
        q = '''add {inet:fqdn | graph 2 --filter { -#nope } } inet:f-M +1 { [ graph:node='*' :type=m1]}'''
        correct = (
            'add',
            '{inet:fqdn | graph 2 --filter { -#nope } }',
            'inet:f-M',
            '+1',
            "{ [ graph:node='*' :type=m1]}"
            )
        parser = s_grammar.Parser(q)
        args = parser.stormcmdargs()
        self.eq(args, correct)

    def test_parse_float(self):
        self.raises(s_exc.BadSyntax, s_grammar.parse_float, 'visi', 0)
        self.eq((4.2, 3), s_grammar.parse_float('4.2', 0))
        self.eq((-4.2, 4), s_grammar.parse_float('-4.2', 0))
        self.eq((-4.2, 8), s_grammar.parse_float('    -4.2', 0))
        self.eq((-4.2, 8), s_grammar.parse_float('    -4.2', 2))

    def test_nom(self):
        self.eq(('xyz', 10), s_grammar.nom('   xyz    ', 0, 'wxyz', trim=True))

    def test_parse_cmd_string(self):
        self.eq(('newp', 9), s_grammar.parse_cmd_string('help newp', 5))

    def test_syntax_error(self):
        query = 'test:str --> *'
        parser = s_grammar.Parser(query)
        self.raises(s_exc.BadSyntax, parser.query)

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

def gen_parse_list():
    '''
    Prints out the Asts for a list of queries in order to compare ASTs between versions of parsers
    '''
    import synapse.lib.syntax as s_syntax  # type: ignore

    retn = []
    for i, query in enumerate(_Queries):
        parser = s_syntax.Parser(query)
        tree = parser.query()
        retn.append(str(tree))
    return retn

def print_parse_list():
    for i in gen_parse_list():
        print(f'    {repr(i)},')
