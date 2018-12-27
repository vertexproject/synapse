import synapse.tests.utils as s_t_utils
from lark import Lark

_Queries = [
    'inet:fqdn',
    '#foo',
    'help',
    'syn:tag',
    'teststr',
    '.created',
    '#hehe.haha',
    'teststr=foo',
    'teststr=$foo',
    '.created<2010',
    '.created>2010',
    'iden deadb33f',
    'testcomp -> *',
    'testint:loc=u',
    'testint:loc=""',
    'testint:loc^=u',
    'testint:loc=us',
    'teststr~="zip"',
    '.created="2001"',
    '.favcolor~="^r"',
    'testint:loc^=""',
    'testint:loc^=23',
    'testint +:loc=u',
    'testint:loc^=us',
    'testint +:loc=""',
    'testint +:loc^=u',
    'testint +:loc=us',
    'testint:loc^=us.',
    'testint:loc=us.v',
    'teststr %limit=1',
    'file:bytes:size=4',
    'movetag #a.b #a.m',
    'syn:tag=a.b +#foo',
    'testint +:loc^=""',
    'testint +:loc^=23',
    'testint +:loc^=us',
    'testint:loc^=us.v',
    'testint:loc=us.va',
    '[ inet:ipv4=$foo ]',
    'pivcomp | noderefs',
    'testint +:loc^=us.',
    'testint +:loc=us.v',
    'testint:loc^=us.va',
    'movetag #hehe #woot',
    '[testint=3 :loc=""]',
    'testint +:loc^=us.v',
    'testint +:loc=us.va',
    'testint:loc^=us.va.',
    'teststr +#foo@=2016',
    'teststr +:tick=2015',
    'pivcomp=(hehe,haha)',
    '[pivcomp=(foo, 123)]',
    '[testint=12 :loc=us]',
    'testint +:loc^=us.va',
    'testint:loc=us.va.sy',
    'inet:ipv4=10.2.1.1/28',
    '[ inet:ipv4=1.2.3.4 ]',
    'testint +:loc^=us.va.',
    'seen:source=$sorc -> *',
    'testcomp:haha~="^lulz"',
    'testint=123 | noderefs',
    'testint +:loc=us.va.sy',
    'teststr +:tick@=(2015)',
    'sudo | [ testguid="*" ]',
    '[testcomp=(1234, 5678)]',
    '[testint=10 :loc=us.va]',
    'testint:loc^=us.va.fair',
    'testint:loc=us.va.syria',
    'teststr=foo +#lol@=2014',
    'teststr | noderefs -d 3',
    'inet:ipv4=192.168.1.0/24',
    'inet:user | limit --woot',
    'testint:loc=us.va.sydney',
    'inet:ipv4=1.2.3.1-1.2.3.3',
    'pivcomp | noderefs --join',
    'testint +:loc^=us.va.fair',
    'teststr=woot +.seen@=2012',
    'teststr=woot +.seen@=#bar',
    'inet:ipv4=1.2.3.4|limit 20',
    'inet:ipv4 | reindex --subs',
    'sudo | testint=6 | delnode',
    'syn:tag=aaa.barbarella.ddd',
    '[testguid=abcd :tick=2015]',
    'testint=123 | noderefs -te',
    '[testint=9 :loc=us.ओं]',
    'testint:loc^=us.va.fairfax',
    'testint +:loc=us.va.sydney',
    'teststr | noderefs -d 3 -u',
    'teststr +:tick@=("-1 day")',
    '.created*range=(2010, 3001)',
    '[inet:ipv4=1.2.3.1-1.2.3.3]',
    '[ inet:ipv4=192.168.1.0/24]',
    'pivtarg=hehe [ .seen=2015 ]',
    'ps:person=$pers -> has -> *',
    'testint:loc^=us.va.fairfax.',
    '[teststr=beep teststr=boop]',
    'teststr +#foo@=(2015, 2018)',
    '[ teststr=foo teststr=bar ]',
    '.created*range=("2010", "?")',
    'geo:place=$place <- has <- *',
    'seen:source=$sorc :node -> *',
    'testcomp -> * | uniq | count',
    '[testint=1 :loc=us.va.syria]',
    'testint +:loc^=us.va.fairfax',
    'testint +:loc="us.va. syria"',
    '[testint=2 :loc=us.va.sydney]',
    'testint +:loc^=us.va.fairfax.',
    'movetag #aaa.b #aaa.barbarella',
    'pivcomp | noderefs --join -d 3',
    'ps:person=$pers -> wentto -> *',
    'ps:person=$pers -> wentto -> *',
    '[testint=4 :loc=us.va.fairfax]',
    '$bar=5.5.5.5 [ inet:ipv4=$bar ]',
    'inet:ipv4 -inet:ipv4=1.2.3.0/30',
    'inet:ipv4 +inet:ipv4=1.2.3.0/30',
    '[testint=8 :loc=us.ca.sandiego]',
    'teststr +#foo@=(2014, 20141231)',
    'teststr +:tick=(2015, "+1 day")',
    'teststr +:tick@=(now, "-1 day")',
    'inet:ipv4 +inet:ipv4=10.2.1.4/31',
    'inet:ipv4 +inet:ipv4=10.2.1.4/32',
    'teststr | noderefs -d 3 --unique',
    'teststr +:tick@=(2015, "+1 day")',
    'teststr=woot +.seen@=(2012,2013)',
    'teststr=woot +.seen@=(2012,2015)',
    '[ inet:dns:a=(woot.com,1.2.3.4) ]',
    'pivcomp | noderefs -j --degrees 2',
    'testint:loc^=us.va.fairfax.reston',
    "[ teststr=abcd :tick=2015 +#cool ]"
    'teststr=pennywise | noderefs -d 3',
    'teststr +:tick@=("now-1day", "?")',
    'teststr +:tick=($test, "+- 2day")',
    'ps:person=$pers -> wentto :n2 -> *',
    '[ teststr=foo teststr=bar ] | spin',
    '[teststr=hehe] | iden abcd | count',
    'teststr:tick=(20131231, "+2 days")',
    'cluster=abcd | noderefs -d 2 --join',
    'ps:person=$pers -> has -> geo:place',
    'ps:person=$pers -> has -> inet:ipv4',
    '[seen=(abcd, (teststr, pennywise))]',
    'testint +:loc^=us.va.fairfax.reston',
    'teststr +:tick=(20150102, "-3 day")',
    'teststr +:tick=(20150201, "+1 day")',
    'teststr=woot $foo=#foo +.seen@=$foo',
    'geo:place:latlong*near=((0, 0), 50m)',
    'geo:place=$place <- has <- inet:ipv4',
    'geo:place=$place <- has <- ps:person',
    'inet:ipv4 +inet:ipv4=1.2.3.1-1.2.3.3',
    'testint:loc^=us.va.fairfax.chantilly',
    'teststr +:tick=(20150102, "+- 2day")',
    'teststr +:tick@=(20150102, "-4 day")',
    'iden 2cdd997872b10a65407ad5fadfa28e0d',
    'pivcomp | noderefs --join --degrees 2',
    'testguid +testguid*range=(abcd, dcbe)',
    '[testint=5 :loc=us.va.fairfax.reston]',
    'inet:user | limit 10 | +inet:user=visi',
    'ps:person=$pers -> wentto -> inet:ipv4',
    'testcomp -> testint',
    '[testint=7 :loc=us.va.fairfax.herndon]',
    'testint +:loc^=us.va.fairfax.chantilly',
    'teststr=123 | noderefs --traverse-edge',
    '[inet:dns:query=(tcp://1.2.3.4, "", 1)]',
    '[refs=((teststr, 123), (testint, 123))]',
    'testcomp +:haha*range=(grinch, meanone)',
    'teststr=123 [:baz="testguid:tick=2015"]',
    'teststr +:tick@=("now+2days", "-3 day")',
    '[ geo:place="*" :latlong=(-30.0,20.22) ]',
    '[ inet:fqdn=woot.com +#bad=(2015,2016) ]',
    'teststr=pennywise | noderefs --join -d 9',
    'teststr +:tick@=(20150102+1day, "-4 day")',
    'teststr +:tick*range=(19701125, 20151212)',
    '[ inet:ipv4=1.2.3.0/30 inet:ipv4=5.5.5.5 ]',
    'teststr=pennywise | noderefs -d 3 -ot=omit',
    'inet:ipv4=1.2.3.4 +( { -> inet:dns:a }<=1 )',
    'inet:ipv4=1.2.3.4 +( { -> inet:dns:a }>=3 )',
    'teststr=a +:tick*range=(20000101, 20101201)',
    '[testint=6 :loc=us.va.fairfax.restonheights]',
    'teststr=pennywise | noderefs -d 3 -of=source',
    'geo:place:latlong*near=((34.1, -118.3), 10km)',
    'teststr=pennywise | noderefs -d 3 -otf=source',
    'geo:place -:latlong*near=((34.1, -118.3), 50m)',
    'inet:asn=10 | noderefs -of inet:ipv4 --join -d 3',
    'teststr +:bar*range=((teststr, c), (teststr, q))',
    'teststr=pennywise | noderefs -d 3 --omit-tag=omit',
    '[ inet:dns:a=(woot.com,1.2.3.4) .seen=(2015,2016) ]',
    'inet:dns:a=(woot.com,1.2.3.4) [ .seen=(2015,2018) ]',
    '[inet:dns:query=(tcp://1.2.3.4, "foo*.haha.com", 1)]',
    '[ pivcomp=(hehe,haha) :tick=2015 +#foo=(2014,2016) ]',
    '[refs=((testint, 16), (testcomp, (9999, greenham)))]',
    'teststr=pennywise | noderefs -d 3 --omit-form=source',
    'inet:dns:a=(woot.com,1.2.3.4) $hehe=:fqdn -:fqdn=$hehe',
    'inet:dns:a=(woot.com,1.2.3.4) $hehe=:fqdn +:fqdn=$hehe',
    'geo:place +geo:place:latlong*near=((34.1, -118.3), 10km)',
    'inet:dns:query=(tcp://1.2.3.4, "", 1) :name -> inet:fqdn',
    '[source=abcd +#omit.nopiv] [seen=(abcd, (pivtarg, foo))]',
    'teststr=pennywise | noderefs --join -d 9 --traverse-edge',
    'inet:dns:a=(woot.com,1.2.3.4) $hehe=:fqdn inet:fqdn=$hehe',
    '[inet:ipv4=1.2.3.4 :asn=10] [seen=(abcd, (inet:asn, 10))]',
    'geo:place:latlong*near=(("34.118560", "-118.300370"), 50m)',
    'ps:person=$pers -> wentto +:time@=(2014,2017) -> geo:place',
    '[ teststr=woot +#foo=(2015,2018) +#bar .seen=(2014,2016) ]',
    'teststr=pennywise | noderefs -d 3 -ott=omit.nopiv -ott=test',
    'geo:place:latlong*near=(("34.118560", "-118.300370"), 2600m)',
    'testcomp +testcomp*range=((1024, grinch), (4096, zemeanone))',
    'teststr=pennywise | noderefs -d 3 --omit-traversal-form=source',
    'pivcomp=(hehe,haha) $ticktock=#foo -> pivtarg +.seen@=$ticktock',
    "[testcomp=(123, test) testcomp=(123, duck) testcomp=(123, mode)]"
    'inet:fqdn +#bad $fqdnbad=#bad -> inet:dns:a:fqdn +.seen@=$fqdnbad',
    '[refs=((testcomp, (2048, horton)), (testcomp, (4096, whoville)))]',
    'teststr +:.seen*range=((20090601, 20090701), (20110905, 20110906,))',
    '[ inet:dns:a=(woot.com, 1.2.3.4) inet:dns:a=(vertex.link, 1.2.3.4) ]',
    'refs +:n1*range=((testcomp, (1000, green)), (testcomp, (3000, ham)))',
    'inet:dns:query=(tcp://1.2.3.4, "foo*.haha.com", 1) :name -> inet:fqdn',
    'testint | noderefs | +testcomp*range=((1000, grinch), (4000, whoville))',
    '[refs=((testcomp, (9001, "A mean one")), (testcomp, (40000, greeneggs)))]',
    'inet:dns:a=(woot.com,1.2.3.4) $seen=.seen :fqdn -> inet:fqdn [ .seen=$seen ]',
    'teststr=pennywise | noderefs -d 3 --omit-traversal-tag=omit.nopiv --omit-traversal-tag=test',
    'geo:place=abcd $latlong=:latlong $radius=:radius | spin | tel:mob:telem:latlong*near=($latlong, 3km)',
    'for $fqdn in $fqdns { [ inet:fqdn=$fqdn ] }',
    'for ($fqdn, $ipv4) in $dnsa { [ inet:dns:a=($fqdn,$ipv4) ] }',
    'for ($fqdn,$ipv4,$boom) in $dnsa { [ inet:dns:a=($fqdn,$ipv4) ] }',
    '[ inet:dns:a=$blob.split("|") ]',
    '''
        for $foo in $foos {

            ($fqdn, $ipv4) = $foo.split("|")

            [ inet:dns:a=($fqdn, $ipv4) ]
        } ''',
    ''' /* A comment */ testint ''',
    ''' testint // a comment''',
    '''/* multi
         line */ testint ''',
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
                    --pivot { <- seen <- source }
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
]

class GrammarTest(s_t_utils.SynTest):

    def test_grammar(*args):
        grammar = open('synapse/lib/storm.g').read()

        parser = Lark(grammar, start='query', debug=True)

        for i, query in enumerate(_Queries):
            # if i < 223:
            #     continue

            # print(f'#{i} {{{query}}}:')
            tree = parser.parse(query)
            # print(f'{tree.pretty()}\n)')

