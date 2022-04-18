import synapse.exc as s_exc

import synapse.lib.scrape as s_scrape

import synapse.tests.utils as s_t_utils

data0 = '''

visi@vertex.link is an email address

and BOB@WOOT.COM is another

    hehe.taxi

    id=mcafee.support.customer.com

    pound£.com

    dollar$.com

    math+sign1.com

    math⁺sign2.com

    math=sign3.com

    math₌sign4.com

    small˜tilde.com

    aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa

    aa:bb:cc:dd:ee:ff

    1.2.3.4

    5.6.7.8:16

    faß.de

    👁️👄👁️.fm

    👁👄👁.com

    vĕrtex.com

    vertex…net

    vĕr-tex.link

    xn--asdf.link

    foo(．)bar[。]baz｡lol

    ۽0--asdf.com

    foo.com.c

    foo.com．c

    foobar.com． 

    baz.com．

    bar.com．
'''

data1 = '''
    tcp://foo[.]bar[.]org:4665/,
    tcp://foo[.]bar[.]org:4665/.
    tcp://foo.bar.org:4665/.,.
    tcp://foo.bar.org:4665/,.,
    tcp://foo.bar.org:4665/,,..a
'''

data2 = '''
A bunch of prefixed urls

<https://www.foobar.com/things.html>

(https://blog.newp.com/scrape/all/the/urls)

[https://www.thingspace.com/blog/giggles.html]

{https://testme.org/test.php}

https://c2server.com/evil/malware/doesnot[care+]aboutstandards{at-all}

'''

data3 = '''
<https://www.foobar.com/things.html>

bech32 segwit values from bip0173
Mainnet P2WPKH: bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4
Testnet P2WPKH: tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx

(https://blog.newp.com/scrape/all/the/urls)

what is this hxxp[:]//foo(.)com noise

[https://www.thingspace.com/blog/giggles.html]

{https://testme.org/test.php}

nothing hxxp[:]//bar(.)com madness

eip-55 address test vectors
# All caps
0x52908400098527886E0F7030069857D2E4169EE7
0x8617E340B3D01FA5F11F306F4090FD50E238070D

'''

btc_addresses = '''
1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2

# Fails checksum
1BvBMSEYstWetqTFn5Au4m4GFg7xJaNNN2

# No match
2BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2

another16ftSEQ4ctQFDtVZiUBusQUjRrGhM3JYweLikeString

bound in some16ftSEQ4ctQFDtVZiUBusQUjRrGhM3JYwe words
and other 16ftSEQ4ctQFDtVZiUBusQUjRrGhM3JYwecharactesr
and bare 16ftSEQ4ctQFDtVZiUBusQUjRrGhM3JYwe
it'll be found

a p2sh hash also

3279PyBGjZTnu1GNSXamReTj98kiYgZdtW

and another

3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy

invalid
3279PyBGjZTnu1GNSXamReTj98kiYgZdtX

bech32 segwit values from bip0173
Mainnet P2WPKH: bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4
Testnet P2WPKH: tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx
Mainnet P2WSH: bc1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3qccfmv3
Testnet P2WSH: tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k7

bc1pw508d6qejxtdg4y5r3zarvary0c5xw7kw508d6qejxtdg4y5r3zarvary0c5xw7k7grplx

# regtest
bcrt1qs758ursh4q9z627kt3pp5yysm78ddny6txaqgw

# all uppercase
TB1QRP33G0Q5C5TXSP9ARYSRX4K6ZDKFS4NCE4XJ0GDCCCEFVPYSXF3Q0SL5K7

# mixed case - reject it
tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sL5k7

Newpnet bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t5
newpnet tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k8


# invalid witness version
BC13W508D6QEJXTDG4Y5R3ZARVARY0C5XW7KN40WF2

# invalid program lengths
bc1rw5uspcuh
bc10w508d6qejxtdg4y5r3zarvary0c5xw7kw508d6qejxtdg4y5r3zarvary0c5xw7kw5rljs90
# bad program length
BC1QR508D6QEJXTDG4Y5R3ZARVARYV98GJ9P
# zero padding > 4 bits
bc1zw508d6qejxtdg4y5r3zarvaryvqyzf3du
# bad conversion?
tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3pjxtptv

# empty data
bc1gmk9yu
'''

eth_addresses = '''
demo address 0x001d3f1ef827552ae1114027bd3ecf1f086ba0f9

eip-55 address test vectors
# All caps
0x52908400098527886E0F7030069857D2E4169EE7
0x8617E340B3D01FA5F11F306F4090FD50E238070D
# All Lower
0xde709f2102306220921060314715629080e2fb77
0x27b1fdb04752bbc536007a920d24acb045561c26
# Normal
0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed
0xfB6916095ca1df60bB79Ce92cE3Ea74c37c5d359
0xdbF03B407c01E7cD3CBea99509d93f8DDDC8C6FB
0xD1220A0cf47c7B9Be7A2E6BA89F429762e7b9aDb

# Real world where someone upper() the whole string
0X633B354CF215DFF4FF3D686AFF363FA0132877F3

# Bad vectors!
0x8617E340B3D01FA5F11F306F4090FD50E238070d
0x27B1fdb04752bbc536007a920d24acb045561c26
0xfB6916095ca1df60bB79Ce92cE3Ea74c37C5D359
'''

bch_addresses = '''
bitcoin cash address
bitcoincash:qqeht8vnwag20yv8dvtcrd4ujx09fwxwsqqqw93w88
#testnet
bchtest:pqc3tyspqwn95retv5k3c5w4fdq0cxvv95u36gfk00
# another valu but in uppercase
BITCOINCASH:QQKV9WR69RY2P9L53LXP635VA4H86WV435995W8P2H

# Bad - mixed case
BITCOINCASH:qqkv9WR69RY2P9L53LXP635VA4H86WV435995W8P2h

# Bad csums
bitcoincash:qqeht8vnwag20yv8dvtcrd4ujx09fwxwsqqqw93w89
bitcoincash:aqkv9wr69ry2p9l53lxp635va4h86wv435995w8p2h
bitcoincash:qqqqqqqq9ry2p9l53lxp635va4h86wv435995w8p2h
'''

xrp_addresses = '''
XRP addresses
rG2ZJRab3EGBmpoxUyiF2guB3GoQTwMGEC
rfBKzgkPt9EvSJmk1uhoWTauaFCaRh4jMp
rLUEXYuLiQptky37CqLcm9USQpPiz5rkpD
# xddresses
X7AcgcsBL6XDcUb289X4mJ8djcdyKaB5hJDWMArnXr61cqZ
# case sensitivity is checked during validation so this fails
x7acgcsbl6xdcub289x4mj8djcdykab5hjdwmarnxr61cqz
# invalid xaddress
XVLhHMPHU98es4dbozjVtdWzVrDjtV18pX8zeUygYrCgrPh
# tagged addr
ripple:rG2ZJRab3EGBmpoxUyiF2guB3GoQTwMGEC'

# Bad addreses
rU6K7V3Po4snVhBBaU29sesqs2qTQJWDw2
rECnmynR4QWrx3TscC5d8x5kCJZ3TDRZjzs

# special addresses
rrrrrrrrrrrrrrrrrrrrrhoLvTp
rrrrrrrrrrrrrrrrrrrrBZbvji
rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh
rrrrrrrrrrrrrrrrrNAMEtxvNvQ
rrrrrrrrrrrrrrrrrrrn5RM1rHd
'''

substrate_addresses = '''
# This is a DOT address
12uxb9baJaiHhCvMzijnCYbkiXpGQ24jhj4AmhNvrMEzWuoV
1FRMM8PEiWXYax7rpS6X4XZX1aAAxSWx1CrKTyrVYhV24fg

# KSM addresses
JL1eTcbzuZP99FjeySkDrMygNREPdbhRyV7iD5AsV4fDRcg
CpjsLDC1JFyrhm3ftC9Gs4QoyrkHKhZKtK7YqGTRFtTafgp

# This is a generic substrate address - we don't scrape these
5DyfSpLWSoSpFfur35gn4PmbrupchiWbdEKgcQPaJGDULHGd

# invalid addresses
1FRMM8PEiWXYax7rpS6X4XZX1aAAxSWx1CrKTyrVYhV24fh
CxDDSH8gS7jecsxaRL8Txf8H5kqesLXAEAEgp76Yz632J9M
pjsLDC1JFyrhm3ftC9Gs4QoyrkHKhZKtK7YqGTRFtTafgp
EVH78gP5ATklKjHonVpxM8c1W6rWPKn5cAS14fXn4Ry5NxK

# random addresses
2q5qF1LqDpINWGC1JJaCzmPQMGPZPKQ76f2XqzxMBjwmadxW
jRaQ6PPzcqNnckcLStwqrTjEvpKnJUP2Jw65Ut36LQQUycd
4dFhts6694CTKKV4btQdnzB3yzxrNcjUVaztvJXmX8eYeXox
'''

cardano_addresses = '''
# byron - icarus style
Ae2tdPwUPEZFRbyhz3cpfC2CumGzNkFBN2L42rcUc2yjQpEkxDbkPodpMAi
Ae2tdPwUPEYzs5BRbGcoS3DXvK8mwgggmESz4HqUwMyaS9eNksZGz1LMS9v
Ae2tdPwUPEYxYNJw1He1esdZYvjmr4NtPzUsGTiqL9zd8ohjZYQcwu6kom7
# byron - daedalus style
DdzFFzCqrhtCNjPk5Lei7E1FxnoqMoAYtJ8VjAWbFmDb614nNBWBwv3kt6QHJa59cGezzf6piMWsbK7sWRB5sv325QqWdRuusMqqLdMt
DdzFFzCqrhsfdzUZxvuBkhV8Lpm9p43p9ubh79GCTkxJikAjKh51qhtCFMqUniC5tv5ZExyvSmAte2Du2tGimavSo6qSgXbjiy8qZRTg
# shelly era
addr1vpu5vlrf4xkxv2qpwngf6cjhtw542ayty80v8dyr49rf5eg0yu80w
addr1v8fet8gavr6elqt6q50skkjf025zthqu6vr56l5k39sp9aqlvz2g4

# Newp
Ae2tdPwUPEZFRbyhz3cpfC2CumGzNkFBN2L42rcUc2yjQpEkxDbkPodpMAX
Ae2tdPwUPEZFRbyhz3cpfC2CumGzNkFBN2L42rcUc2yjQpEkxDbkPodddMAX
Ae2tdPWUPEZFRbyhz3cpfC2CumGzNkFBN2L42rcUc2yjQpEkxDbkPodpMAi
DdzFFzCqrhsfdzUZxvuBkhV8Lpm9p43p9ubh79GCTkxJikAjKh51qhtCFMqUniC5tv5ZExyvSmAte2Du2tGimavSo6qSgXbjiy8qZRTX
addr1vpu5vlrf4xkxv2qpwngf6cjhtw542ayty80v8dyr49rf5eg0yu80X
addr1vpu5vlrf4xkxv2qpwngf6cjhtw542ayty80v8dyr49rf5eg0yu80W
'''

class ScrapeTest(s_t_utils.SynTest):

    def test_scrape_basic(self):
        forms = s_scrape.getForms()
        self.isin('inet:ipv4', forms)
        self.isin('crypto:currency:address', forms)
        self.notin('inet:web:message', forms)

        with self.raises(s_exc.BadArg):
            s_scrape.genFangRegex({'hehe': 'haha', 'newp': 'bignope'})

        ndefs = list(s_scrape.scrape('log4j vuln CVE-2021-44228 is pervasive'))
        self.eq(ndefs, (('it:sec:cve', 'CVE-2021-44228'),))

        infos = list(s_scrape.contextScrape('endashs are a vulnerability  CVE\u20132022\u20131138 '))
        self.eq(infos, [{'match': 'CVE–2022–1138', 'offset': 29, 'valu': 'CVE-2022-1138', 'form': 'it:sec:cve'}])

        nodes = set(s_scrape.scrape(data0))

        self.len(26, nodes)
        nodes.remove(('hash:md5', 'a' * 32))
        nodes.remove(('inet:ipv4', '1.2.3.4'))
        nodes.remove(('inet:ipv4', '5.6.7.8'))
        nodes.remove(('inet:fqdn', 'bar.com'))
        nodes.remove(('inet:fqdn', 'baz.com'))
        nodes.remove(('inet:fqdn', 'foobar.com'))
        nodes.remove(('inet:fqdn', 'WOOT.COM'))
        nodes.remove(('inet:fqdn', 'hehe.taxi'))
        nodes.remove(('inet:fqdn', 'vertex.link'))
        nodes.remove(('inet:fqdn', 'vĕrtex.com'))
        nodes.remove(('inet:fqdn', 'vĕr-tex.link'))
        nodes.remove(('inet:fqdn', 'faß.de'))
        nodes.remove(('inet:fqdn', '👁️👄👁️.fm'))
        nodes.remove(('inet:fqdn', '👁👄👁.com'))
        nodes.remove(('inet:fqdn', 'foo．bar。baz｡lol'))
        nodes.remove(('inet:fqdn', 'xn--asdf.link'))
        nodes.remove(('inet:fqdn', 'mcafee.support.customer.com'))
        nodes.remove(('inet:fqdn', 'pound£.com'))
        nodes.remove(('inet:fqdn', 'sign1.com'))
        nodes.remove(('inet:fqdn', 'sign2.com'))
        nodes.remove(('inet:fqdn', 'sign3.com'))
        nodes.remove(('inet:fqdn', 'sign4.com'))
        nodes.remove(('inet:fqdn', 'tilde.com'))
        nodes.remove(('inet:server', '5.6.7.8:16'))
        nodes.remove(('inet:email', 'BOB@WOOT.COM'))
        nodes.remove(('inet:email', 'visi@vertex.link'))
        self.len(0, nodes)

        nodes = set(s_scrape.scrape(data0, 'inet:email'))
        self.len(2, nodes)
        nodes.remove(('inet:email', 'BOB@WOOT.COM'))
        nodes.remove(('inet:email', 'visi@vertex.link'))
        self.len(0, nodes)

        nodes = list(s_scrape.scrape(data1))
        self.len(10, nodes)
        for _ in range(5):
            nodes.remove(('inet:fqdn', 'foo.bar.org'))

        # URLs should not include any trailing periods or commas.
        nodes.remove(('inet:url', 'tcp://foo.bar.org:4665/'))
        nodes.remove(('inet:url', 'tcp://foo.bar.org:4665/'))
        nodes.remove(('inet:url', 'tcp://foo.bar.org:4665/'))
        nodes.remove(('inet:url', 'tcp://foo.bar.org:4665/'))
        nodes.remove(('inet:url', 'tcp://foo.bar.org:4665/,,..a'))

        nodes = list(s_scrape.scrape(data2))
        nodes.remove(('inet:url', 'https://www.foobar.com/things.html'))
        nodes.remove(('inet:url', 'https://blog.newp.com/scrape/all/the/urls'))
        nodes.remove(('inet:url', 'https://www.thingspace.com/blog/giggles.html'))
        nodes.remove(('inet:url', 'https://testme.org/test.php'))
        nodes.remove(('inet:url', 'https://c2server.com/evil/malware/doesnot[care+]aboutstandards{at-all}'))

        nodes = list(s_scrape.scrape(btc_addresses))
        self.len(11, nodes)
        nodes.remove(('crypto:currency:address',
                      ('btc', '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2')))
        nodes.remove(('crypto:currency:address',
                      ('btc', '16ftSEQ4ctQFDtVZiUBusQUjRrGhM3JYwe')))
        nodes.remove(('crypto:currency:address',
                      ('btc', '3279PyBGjZTnu1GNSXamReTj98kiYgZdtW')))
        nodes.remove(('crypto:currency:address',
                      ('btc', '3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy')))
        nodes.remove(('crypto:currency:address',
                      ('btc', 'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4')))
        nodes.remove(('crypto:currency:address',
                      ('btc', 'tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx')))
        nodes.remove(('crypto:currency:address',
                      ('btc', 'bcrt1qs758ursh4q9z627kt3pp5yysm78ddny6txaqgw')))
        nodes.remove(('crypto:currency:address',
                      ('btc', 'bc1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3qccfmv3')))
        nodes.remove(('crypto:currency:address',
                      ('btc', 'tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k7')))
        nodes.remove(('crypto:currency:address',
                      ('btc', 'tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k7')))
        nodes.remove(('crypto:currency:address',
                      ('btc', 'bc1pw508d6qejxtdg4y5r3zarvary0c5xw7kw508d6qejxtdg4y5r3zarvary0c5xw7k7grplx')))
        self.len(0, nodes)

        nodes = list(s_scrape.scrape(eth_addresses))
        self.len(10, nodes)
        nodes.remove(('crypto:currency:address',
                      ('eth', '0x001d3f1ef827552ae1114027bd3ecf1f086ba0f9')))
        nodes.remove(('crypto:currency:address',
                      ('eth', '0x52908400098527886e0f7030069857d2e4169ee7')))
        nodes.remove(('crypto:currency:address',
                      ('eth', '0x8617e340b3d01fa5f11f306f4090fd50e238070d')))
        nodes.remove(('crypto:currency:address',
                      ('eth', '0xde709f2102306220921060314715629080e2fb77')))
        nodes.remove(('crypto:currency:address',
                      ('eth', '0x27b1fdb04752bbc536007a920d24acb045561c26')))
        nodes.remove(('crypto:currency:address',
                      ('eth', '0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed')))
        nodes.remove(('crypto:currency:address',
                      ('eth', '0xfB6916095ca1df60bB79Ce92cE3Ea74c37c5d359')))
        nodes.remove(('crypto:currency:address',
                      ('eth', '0xdbF03B407c01E7cD3CBea99509d93f8DDDC8C6FB')))
        nodes.remove(('crypto:currency:address',
                      ('eth', '0xD1220A0cf47c7B9Be7A2E6BA89F429762e7b9aDb')))
        nodes.remove(('crypto:currency:address',
                      ('eth', '0x633b354cf215dff4ff3d686aff363fa0132877f3')))
        self.len(0, nodes)

        nodes = list(s_scrape.scrape(bch_addresses))
        self.len(3, nodes)
        nodes.remove(('crypto:currency:address',
                      ('bch', 'bitcoincash:qqeht8vnwag20yv8dvtcrd4ujx09fwxwsqqqw93w88')))
        nodes.remove(('crypto:currency:address',
                      ('bch', 'bchtest:pqc3tyspqwn95retv5k3c5w4fdq0cxvv95u36gfk00')))
        nodes.remove(('crypto:currency:address',
                      ('bch', 'bitcoincash:qqkv9wr69ry2p9l53lxp635va4h86wv435995w8p2h')))

        nodes = list(s_scrape.scrape(xrp_addresses))
        self.len(10, nodes)
        nodes.remove(('crypto:currency:address', ('xrp', 'rG2ZJRab3EGBmpoxUyiF2guB3GoQTwMGEC')))
        nodes.remove(('crypto:currency:address', ('xrp', 'rfBKzgkPt9EvSJmk1uhoWTauaFCaRh4jMp')))
        nodes.remove(('crypto:currency:address', ('xrp', 'rLUEXYuLiQptky37CqLcm9USQpPiz5rkpD')))
        nodes.remove(('crypto:currency:address',
                      ('xrp', 'X7AcgcsBL6XDcUb289X4mJ8djcdyKaB5hJDWMArnXr61cqZ')), )
        nodes.remove(('crypto:currency:address', ('xrp', 'rG2ZJRab3EGBmpoxUyiF2guB3GoQTwMGEC')))
        nodes.remove(('crypto:currency:address', ('xrp', 'rrrrrrrrrrrrrrrrrrrrrhoLvTp')))
        nodes.remove(('crypto:currency:address', ('xrp', 'rrrrrrrrrrrrrrrrrrrrBZbvji')))
        nodes.remove(('crypto:currency:address', ('xrp', 'rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh')))
        nodes.remove(('crypto:currency:address', ('xrp', 'rrrrrrrrrrrrrrrrrNAMEtxvNvQ')))
        nodes.remove(('crypto:currency:address', ('xrp', 'rrrrrrrrrrrrrrrrrrrn5RM1rHd')))

        nodes = list(s_scrape.scrape(substrate_addresses))
        self.len(4, nodes)
        nodes.remove(('crypto:currency:address',
                      ('dot', '12uxb9baJaiHhCvMzijnCYbkiXpGQ24jhj4AmhNvrMEzWuoV')))
        nodes.remove(('crypto:currency:address',
                      ('dot', '1FRMM8PEiWXYax7rpS6X4XZX1aAAxSWx1CrKTyrVYhV24fg')))
        nodes.remove(('crypto:currency:address',
                      ('ksm', 'JL1eTcbzuZP99FjeySkDrMygNREPdbhRyV7iD5AsV4fDRcg')))
        nodes.remove(('crypto:currency:address',
                      ('ksm', 'CpjsLDC1JFyrhm3ftC9Gs4QoyrkHKhZKtK7YqGTRFtTafgp')))

        nodes = list(s_scrape.scrape(cardano_addresses))
        self.len(7, nodes)
        nodes.remove(('crypto:currency:address',
                      ('ada', 'Ae2tdPwUPEZFRbyhz3cpfC2CumGzNkFBN2L42rcUc2yjQpEkxDbkPodpMAi')))
        nodes.remove(('crypto:currency:address',
                      ('ada', 'Ae2tdPwUPEYzs5BRbGcoS3DXvK8mwgggmESz4HqUwMyaS9eNksZGz1LMS9v')))
        nodes.remove(('crypto:currency:address',
                      ('ada', 'Ae2tdPwUPEYxYNJw1He1esdZYvjmr4NtPzUsGTiqL9zd8ohjZYQcwu6kom7')))
        nodes.remove(('crypto:currency:address',
                      ('ada',
                       'DdzFFzCqrhtCNjPk5Lei7E1FxnoqMoAYtJ8VjAWbFmDb614nNBWBwv3kt6QHJa59cGezzf6piMWsbK7sWRB5sv325QqWdRuusMqqLdMt')))
        nodes.remove(('crypto:currency:address',
                      ('ada',
                       'DdzFFzCqrhsfdzUZxvuBkhV8Lpm9p43p9ubh79GCTkxJikAjKh51qhtCFMqUniC5tv5ZExyvSmAte2Du2tGimavSo6qSgXbjiy8qZRTg')))
        nodes.remove(('crypto:currency:address',
                      ('ada', 'addr1vpu5vlrf4xkxv2qpwngf6cjhtw542ayty80v8dyr49rf5eg0yu80w')))
        nodes.remove(('crypto:currency:address',
                      ('ada', 'addr1v8fet8gavr6elqt6q50skkjf025zthqu6vr56l5k39sp9aqlvz2g4')))

    def test_scrape_sequential(self):
        md5 = ('a' * 32, 'b' * 32,)
        sha1 = ('c' * 40, 'd' * 40,)
        sha256 = ('e' * 64, 'f' * 64,)
        url = ('http://foobar.com', 'http://cat.net',)
        ipv4 = ('1.2.3.4', '5.6.7.8',)
        server = ('7.7.7.7:123', '8.8.8.8:456',)
        fqdn = ('woot.com', 'baz.io',)
        email = ('me@bar.io', 'you@zee.com',)

        txt = f'hehe {md5[0]} {md5[1]} haha'
        self.eq({md5[0], md5[1], }, {n[1] for n in s_scrape.scrape(txt)})

        txt = f'hehe {md5[0]},{md5[1]} haha'
        self.eq({md5[0], md5[1], }, {n[1] for n in s_scrape.scrape(txt)})

        txt = f'hehe {sha1[0]} {sha1[1]} haha'
        self.eq({sha1[0], sha1[1], }, {n[1] for n in s_scrape.scrape(txt)})

        txt = f'hehe {sha256[0]} {sha256[1]} haha'
        self.eq({sha256[0], sha256[1], }, {n[1] for n in s_scrape.scrape(txt)})

        txt = f'hehe {url[0]} {url[1]} haha'
        self.eq({url[0], 'foobar.com', url[1], 'cat.net', }, {n[1] for n in s_scrape.scrape(txt)})

        txt = f'hehe {ipv4[0]} {ipv4[1]} haha'
        self.eq({ipv4[0], ipv4[1], }, {n[1] for n in s_scrape.scrape(txt)})

        txt = f'hehe {server[0]} {server[1]} haha'
        self.eq({server[0], '7.7.7.7', server[1], '8.8.8.8', }, {n[1] for n in s_scrape.scrape(txt)})

        txt = f'hehe "{fqdn[0]}" "{fqdn[1]}" haha'
        self.eq({fqdn[0], fqdn[1], }, {n[1] for n in s_scrape.scrape(txt)})

        txt = f'hehe {fqdn[0]}  {fqdn[1]} haha'
        self.eq({fqdn[0], fqdn[1], }, {n[1] for n in s_scrape.scrape(txt)})

        txt = f'hehe {email[0]}, {email[1]} haha'
        self.eq({email[0], 'bar.io', email[1], 'zee.com', }, {n[1] for n in s_scrape.scrape(txt)})

        txt = f'hehe {fqdn[0]}. {fqdn[1]} haha'
        self.eq({fqdn[0], fqdn[1], }, {n[1] for n in s_scrape.scrape(txt)})

        txt = f'hehe {fqdn[0]},{fqdn[1]} haha'
        self.eq({fqdn[0], fqdn[1], }, {n[1] for n in s_scrape.scrape(txt)})

        txt = f'hehe {fqdn[0]} {fqdn[1]} haha'
        self.eq({fqdn[0], fqdn[1], }, {n[1] for n in s_scrape.scrape(txt)})

        txt = f'hehe {email[0]}. {email[1]} haha'
        self.eq({email[0], 'bar.io', email[1], 'zee.com', }, {n[1] for n in s_scrape.scrape(txt)})

        txt = f'hehe {email[0]} {email[1]} haha'
        self.eq({email[0], 'bar.io', email[1], 'zee.com', }, {n[1] for n in s_scrape.scrape(txt)})

        txt = f'hehe {email[0]} {fqdn[0]} haha'
        self.eq({email[0], 'bar.io', fqdn[0], }, {n[1] for n in s_scrape.scrape(txt)})

        # ensure extra-iana tlds included as tld
        txt = f'hehe woot.onion woot.bit haha'
        self.eq({'woot.onion', 'woot.bit', }, {n[1] for n in s_scrape.scrape(txt)})

    def test_refang(self):
        defanged = '10[.]0[.]0[.]1'
        refanged = '10.0.0.1'
        self.eq({refanged}, {n[1] for n in s_scrape.scrape(defanged)})

        defanged = '10\\.0\\.0\\.1'
        refanged = '10.0.0.1'
        self.eq({refanged}, {n[1] for n in s_scrape.scrape(defanged)})

        defanged = 'www(.)spam(.)net'
        refanged = 'www.spam.net'
        self.eq({refanged}, {n[1] for n in s_scrape.scrape(defanged)})

        defanged = 'http[:]//foo.faz.com[:]12312/bam'
        refanged = 'http://foo.faz.com:12312/bam'
        self.eq({refanged, 'foo.faz.com'}, {n[1] for n in s_scrape.scrape(defanged)})

        defanged = 'hxxp://foo.faz.edu/'
        refanged = 'http://foo.faz.edu/'
        self.eq({refanged, 'foo.faz.edu'}, {n[1] for n in s_scrape.scrape(defanged)})

        defanged = 'hXXps://foo.faz.edu/'
        refanged = 'https://foo.faz.edu/'
        self.eq({refanged, 'foo.faz.edu'}, {n[1] for n in s_scrape.scrape(defanged)})

        defanged = 'FXP://255.255.255.255'
        refanged = 'ftp://255.255.255.255'
        self.eq({refanged, '255.255.255.255'}, {n[1] for n in s_scrape.scrape(defanged)})

        defanged = 'fxps://255.255.255.255'
        refanged = 'ftps://255.255.255.255'
        self.eq({refanged, '255.255.255.255'}, {n[1] for n in s_scrape.scrape(defanged)})

        defanged = 'foo[at]bar.com'
        refanged = 'foo@bar.com'
        self.eq({refanged, 'bar.com'}, {n[1] for n in s_scrape.scrape(defanged)})

        defanged = 'foo[@]bar.com'
        refanged = 'foo@bar.com'
        self.eq({refanged, 'bar.com'}, {n[1] for n in s_scrape.scrape(defanged)})

        defanged = 'Im a text BLOB with 255(.)255(.)255.0 and hxxps[:]yowza(.)baz[.]edu/foofaz'
        exp = {
            'yowza.baz.edu',
            '255.255.255.0'
        }
        self.eq(exp, {n[1] for n in s_scrape.scrape(defanged)})

        defanged = 'HXXP[:]//example.com?faz=hxxp and im talking about HXXP over here'
        exp = {
            'http://example.com?faz=hxxp',
            'example.com'
        }
        self.eq(exp, {n[1] for n in s_scrape.scrape(defanged)})

        defanged = '''hxxp[://]beep-thing[.]com/beep[.]docx
        hxxps[://]beep[.]com/beep/gen[.]stuff
        '''
        exp = {
            'http://beep-thing.com/beep.docx',
            'https://beep.com/beep/gen.stuff',
            'beep-thing.com',
            'beep.com',
        }
        self.eq(exp, {n[1] for n in s_scrape.scrape(defanged)})

        # Test scrape without re-fang
        defanged = 'HXXP[:]//example.com?faz=hxxp and im talking about HXXP over here'
        self.eq({'example.com'}, {n[1] for n in s_scrape.scrape(defanged, refang=False)})

    def test_scrape_context(self):
        results = list(s_scrape.contextScrape(data3))
        r = [r for r in results if r.get('valu') == 'https://www.foobar.com/things.html'][0]
        self.eq(r, {'form': 'inet:url',
                    'match': 'https://www.foobar.com/things.html',
                    'offset': 2,
                    'valu': 'https://www.foobar.com/things.html'})

        r = [r for r in results if r.get('valu') == 'www.thingspace.com'][0]
        self.eq(r, {'form': 'inet:fqdn',
                    'match': 'www.thingspace.com',
                    'offset': 285,
                    'valu': 'www.thingspace.com'}
                )
        r = [r for r in results if r.get('valu') == 'http://foo.com'][0]
        self.eq(r, {'match': 'hxxp[:]//foo(.)com',
                    'offset': 250,
                    'valu': 'http://foo.com',
                    'form': 'inet:url'})
        r = [r for r in results if r.get('valu') == 'http://bar.com'][0]
        self.eq(r, {'match': 'hxxp[:]//bar(.)com',
                    'offset': 363,
                    'valu': 'http://bar.com',
                    'form': 'inet:url'})

        r = [r for r in results if r.get('valu') == ('eth', '0x52908400098527886e0f7030069857d2e4169ee7')][0]
        self.eq(r, {'form': 'crypto:currency:address',
                    'offset': 430,
                    'match': '0x52908400098527886E0F7030069857D2E4169EE7',
                    'valu': ('eth', '0x52908400098527886e0f7030069857d2e4169ee7')}
                )
        # Assert match value matches...
        for r in results:
            erv = r.get('match')
            offs = r.get('offset')
            fv = data3[offs:offs + len(erv)]
            self.eq(erv, fv)
