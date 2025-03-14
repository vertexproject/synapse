from unittest import mock

import regex

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

    # GOOD IPV4 ADDRESSES
    1.2.3.4

    5.6.7.8:16

    The IP address is: 201.202.203.204.

    Typo no space after sentence.211.212.213.214 is the address..

    The IP address is:2.3.4.5.

    # GOOD IPV6 ADDRESSES

    fff0::1
    ::1
    ::1010
    ff::
    0::1
    0:0::1
    ff:fe:fd::1
    ffff:ffe:fd:c::1
    111::333:222
    111:222::333

    1:2:3:4:5:6:7:8

    1:2:3:4:5:6::7
    1:2:3:4:5::6
    1:2:3:4::5
    1:2:3::4
    1:2::3

    1::2
    1::2:3:4:5:6:7
    1::2:3:4:5:6
    1::2:3:4:5
    1::2:3:4
    1::2:3

    a:2::3:4:5:6:7
    a:2::3:4:5:6
    a:2::3:4:5
    a:2::3:4
    a:2::3

    2001:db8:3333:4444:5555:6666:4.3.2.1

    ::3.4.5.6
    ::ffff:4.3.2.2
    ::FFFF:4.3.2.3
    ::ffff:0000:4.3.2.4
    ::1:2:3:4:4.3.2.5
    ::1:2:3:4.3.2.6
    ::1:2:3:4:5:4.3.2.7
    ::ffff:255.255.255.255
    ::ffff:111.222.33.44
    1:2::3:4.3.2.8

    1:2:3:4:5:6:7:9%eth0
    1:2:3:4:5:6:7:a%s10
    1:2:3:4:5:6:7:b%lo
    1::a%eth0
    1::a:3%lo
    1:a::3%eth1

    The IP address is:a:b:c:d:e::6.

    # BAD IPV6 ADDRESSES
    ::
    0::0::1
    1:2:3:4
    1:2:3:4:5
    1:2:3:4:5:6
    1:2:3:4:5:6:7
    ::ffff:4.3.2.a.5
    ::1.3.3.4.5:4.3.2.b
    ::1:2:3:4:5:6:4.3.2.c
    ::1:2:3:4:5:6:7:4.3.2.d

    # Bad IPV4 addresses:
    6.7.8.900
    6.7.8.9750
    1236.7.8.9
    0126.7.8.9
    6.7.8.9.6.7.8.9
    6.7.8.9.6

    # GOOD INET:SERVER
    1.2.3.4:123
    1.2.3.4:65535
    1.2.3.4:12346.
    1.2.3.4:12347:
    [::1]:123
    [1:2:3:4:5:6:7:8]:123

    # BAD INET:SERVER
    1.2.3.4:0
    1.2.3.4:65536
    1.2.3.4:1.2.3.5
    1.2.3.4:123456
    1.2.3.4:
    0.1.2.3.4:12345
    1.2.3:123
    [::1].123
    [::1]:123.1234
    [1:2:3:4]:123

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

    fxp.com

    CWE # no match
    CWE-1
    CWE-12345678
    CWE-123456789 # no match

'''

data1 = '''
    tcp://foo[.]bar[.]org:4665/,
    tcp://foo[.]bar[.]org:4665/.
    tcp://foo.bar.org:4665/.,.
    tcp://foo.bar.org:4665/,.,
    tcp://foo.bar.org:4665/,,..a
    tcp://[1:2:3:4:5:6:7:8]:1234/
    tcp://[1:2:3::4:5:6]:2345/
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

# schema defanged and modified with host defanged as well
hxxp[s]://legitcorp[.]com/blah/giggle.html
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
addr1gx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer5pnz75xxcrzqf96k
addr1yx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzerkr0vd4msrxnuwnccdxlhdjar77j6lg0wypcc9uar5d2shs2z78ve

# Newp
Ae2tdPwUPEZFRbyhz3cpfC2CumGzNkFBN2L42rcUc2yjQpEkxDbkPodpMAX
Ae2tdPwUPEZFRbyhz3cpfC2CumGzNkFBN2L42rcUc2yjQpEkxDbkPodddMAX
Ae2tdPWUPEZFRbyhz3cpfC2CumGzNkFBN2L42rcUc2yjQpEkxDbkPodpMAi
DdzFFzCqrhsfdzUZxvuBkhV8Lpm9p43p9ubh79GCTkxJikAjKh51qhtCFMqUniC5tv5ZExyvSmAte2Du2tGimavSo6qSgXbjiy8qZRTX
addr1vpu5vlrf4xkxv2qpwngf6cjhtw542ayty80v8dyr49rf5eg0yu80X
addr1vpu5vlrf4xkxv2qpwngf6cjhtw542ayty80v8dyr49rf5eg0yu80W
DdzFFzCqrht9wkicvUx4Hc4W9gjCbx1sjsWAie5zLHo2K2R42y2zvA7W9S9dM9bCHE7xtpNriy1EpE5xwv7
'''

linux_paths = '''
# GOOD PATHS
/bin/ls
/bin/foo/bar
/bin/foo\x00
/bin/foo//
/bin/foo//bar
/home/foo/bar/baz.txt
/tmp/foo/bar
/var/run/foo/
/var/run/foo/bar
//var/run/bar
The observed path is:/root/.aaa/bbb
The observed paths are:
 - /root/.aaa/ccc
 - /root/.aaa/ddd
 -/root/.aaa/eee

# BAD PATHS
/
/foo/bar
/foo/bin/ls
foo/bin/ls
bin/ls
bin/foo/bar
bin/foo\x00
bin/foo//
bin/foo//bar
home/foo/bar/baz.txt
tmp/foo/bar
var/run/foo/
var/run/foo/bar
but they not have a open SDK :/.
'''
linux_paths += '\n' + '\n'.join([
    '/bin' + '/long' * 1_024,
    '/bin' + '/a' * 1_024,
])

windows_paths = '''
# GOOD PATHS
c:\\temp
c:\\temp.txt
c:\\windows\\
c:\\windows\\calc.exe
c:\\windows\\system32\\
c:\\windows\\system32\\drivers\\usb.sys
d:\\foo\\bar.txt
d:\\foo\\
d:\\foo
d:\\foo.txt
c:\\\\foo\\bar
The observed path is:c:\\aaa\\bbb
The observed paths are:
 - c:\\aaa\\ccc
 - c:\\aaa\\ddd
 -c:\\aaa\\eee

# BAD PATHS
c:\\windows\\system32\\foo.
c:\\windows\\LPT1
c:\\foo.
dc:\\foo\\bar
'''
windows_paths += '\n' + '\n'.join([
    'c:\\windows' + '\\long' * 7_000,
    'c:\\windows' + '\\a' * 1_024,
])

good_uncs = [
    '\\\\foo\\bar\\baz',
    '\\\\server\\share',
    '\\\\server.domain.com\\share\\path\\to\\filename.txt',
    '\\\\1.2.3.4\\share',
    '\\\\1.2.3.4\\share\\dirn',
    '\\\\1234-2345--3456.ipv6-literal.net\\share',
    '\\\\1234-2345--3456.ipv6-literal.net\\share\\dirn',
    '\\\\1-2-3-4-5-6-7-8.ipv6-literal.net\\share\\filename.txt',
    '\\\\1-2-3-4-5-6-7-8seth0.ipv6-literal.net\\share\\filename.txt',
    '\\\\server@SSL\\share\\foo.txt',
    '\\\\server@1234\\share\\foo.txt',
    '\\\\server@SSL@1234\\share\\foo.txt',
    '\\\\0--1.ipv6-literal.net@SSL@1234\\share\\foo.txt',
    ('\\\\server\\share\\' + ('A' * 250) + '.txt:sname:stype\n'),
    'The UNC path is: \\\\server.domain.com\\share\\path\\to\\filename1.txt',
    'The UNC path is:\\\\server.domain.com\\share\\path\\to\\filename2.txt',
    'The UNC path is: "\\\\badserver\\share\\malicious file with spaces.txt" and the fqdn is badserver.domain.com.',
    "The UNC path is: '\\\\badserver\\share\\malicious file with spaces.txt' and the fqdn is badserver.domain.com.",
    'The UNC path is: \\\\badserver\\share\\filename and the fqdn is badserver.domain.com.',
    '\\\\server@asdf\\share\\filename.txt',
    '\\\\1:2:3:4:5:6:7:8\\share',
    '\\\\[1:2:3:4:5:6:7:8]\\share',
]

bad_uncs = [
    '\\\\server',
    '\\\\server\\',
    '\\\\hostname@SSL',
    '\\\\server\\\\foobar.txt',
    '\\\\server\\AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\\filename.txt',
    ('\\\\server\\share\\' + ('A' * 256) + '\\filename.txt\n'),
    ('\\\\server\\share\\' + ('A' * 256) + '.txt\n'),
]

unc_paths = '\n'.join(good_uncs + bad_uncs)

cpedata = r'''GOOD DATA
cpe:2.3:a:vendor:product:version:update:edition:lng:sw_edition:target_sw:target_hw:other
cpe:2.3:a:vendor:product:version:update:edition:lng:sw_edition:target_sw:target_hw:tspace non matched word
cpe:2.3:a:*:*:*:*:*:*:*:*:*:*
cpe:2.3:h:*:*:*:*:*:*:*:*:*:*
cpe:2.3:o:*:*:*:*:*:*:*:*:*:*
cpe:2.3:-:*:*:*:*:*:*:*:*:*:*
cpe:2.3:*:*:*:*:*:*:*:*:*:*:*
cpe:2.3:*:-:na:*:*:*:*:*:*:*:*
cpe:2.3:*:.:dot:*:*:*:*:*:*:*:*
cpe:2.3:*:_:underscore:*:*:*:*:*:*:*:*

A few quoted characters
cpe:2.3:*:\!:quoted:*:*:*:*:*:*:*:*
cpe:2.3:*:\?:quoted:*:*:*:*:*:*:*:*
cpe:2.3:*:\*:quoted:*:*:*:*:*:*:*:*
cpe:2.3:*:\\:escapeescape:*:*:*:*:*:*:*:*
cpe:2.3:*:langtest:*:*:*:*:-:*:*:*:*
cpe:2.3:*:langtest:*:*:*:*:*:*:*:*:*
cpe:2.3:*:langtest:*:*:*:*:en:*:*:*:*
cpe:2.3:*:langtest:*:*:*:*:usa:*:*:*:*
cpe:2.3:*:langtest:*:*:*:*:usa-en:*:*:*:*
cpe:2.3:*:langtest:*:*:*:*:usa-123:*:*:*:*

A few examples
cpe:2.3:a:ntp:ntp:4.2.8:p3:*:*:*:*:*:*
cpe:2.3:o:microsoft:windows_7:-:sp2:*:*:*:*:*:*
cpe:2.3:a:hp:insight:7.4.0.1570:-:*:*:online:win2003:x64:*
cpe:2.3:a:foo\\bar:big\$money_2010:*:*:*:*:special:ipod_touch:80gb:*
cpe:2.3:a:hp:openview_network_manager:7.51:*:*:*:*:linux:*:*
cpe:2.3:a:apple:swiftnio_http\/2:1.19.1:*:*:*:*:swift:*:*

Some quoted examples
cpe:2.3:a:fooo:bar_baz\:_beep_bpp_sys:1.1:*:*:*:*:ios:*:*
cpe:2.3:a:lemonldap-ng:apache\:\:session\:\:browsable:0.9:*:*:*:*:perl:*:*
cpe:2.3:a:daemon-ng:hurray\:\::0.x:*:*:*:*:*:*:*
cpe:2.3:a:microsoft:intern\^et_explorer:8.0.6001:beta:*:*:*:*:*:*

TEXT examples
Example double quoted cpe value "cpe:2.3:a:vertex:synapse:*:*:*:*:*:*:*:dquotes".
Example double quoted cpe value "cpe:2.3:a:vertex:synapse:*:*:*:*:*:*:*:MiXeDcAsE".
Example single quoted cpe value "cpe:2.3:a:vertex:synapse:*:*:*:*:*:*:*:squotes".
A CPE at the end of a sentence like this captures the period... cpe:2.3:a:*:*:*:*:*:*:*:*:*:hasperiod.
Some CPE are exciting! Like this cpe:2.3:a:*:*:*:*:*:*:*:*:*:noexclaim!
Some CPE are boring! Like this cpe:2.3:a:*:*:*:*:*:*:*:*:*:noslash\
Unicode endings are omitted cpe:2.3:a:*:*:*:*:*:*:*:*:*:unicodeend0ॐ
Unicode quotes “cpe:2.3:a:*:*:*:*:*:*:*:*:*:smartquotes”
cpe:2.3:*:?why??:*:*:*:*:*:*:*:*:*
cpe:2.3:*:*why*:*:*:*:*:*:*:*:*:*

EMBEDDED TEXT
wordscpe:2.3:a:vendor:product:version:update:edition:lng:sw_edition:target_sw:target_hw:otherxxx:newp
wordscpe:2.3:a:vendor:product:version:update:edition:lng:sw_edition:target_sw:target_hw:otherzzz:

BAD values
cpe:2.3:*:?:spec1:*:*:*:*:*:*:*:*
cpe:2.3:a:vertex:synapse:*:*:*:NEWP:*:*:*:*
cpe:2.3:a::::::::::
cpe:2.3:a:vendor:product:version:update:edition:lng:sw_edition:target_sw:ॐ:other
cpe:2.3:a:vendor:product:version:update:edition
cpe:2.3:a:opps:bad_quote\\/2:1.19.1:*:*:*:*:swift:*:*

# Bad languages
cpe:2.3:*:langtest:*:*:*:*:a:*:*:*:*
cpe:2.3:*:langtest:*:*:*:*:aaaa:*:*:*:*
cpe:2.3:*:langtest:*:*:*:*:usa-o:*:*:*:*
cpe:2.3:*:langtest:*:*:*:*:usa-omn:*:*:*:*
cpe:2.3:*:langtest:*:*:*:*:usa-12:*:*:*:*
cpe:2.3:*:langtest:*:*:*:*:usa-1234:*:*:*:*
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

        self.len(83, nodes)
        nodes.remove(('hash:md5', 'a' * 32))
        nodes.remove(('inet:ipv4', '1.2.3.4'))
        nodes.remove(('inet:ipv4', '2.3.4.5'))
        nodes.remove(('inet:ipv4', '5.6.7.8'))
        nodes.remove(('inet:ipv4', '201.202.203.204'))
        nodes.remove(('inet:ipv4', '211.212.213.214'))
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
        nodes.remove(('inet:fqdn', 'fxp.com'))
        nodes.remove(('inet:server', '5.6.7.8:16'))
        nodes.remove(('inet:server', '1.2.3.4:123'))
        nodes.remove(('inet:server', '1.2.3.4:65535'))
        nodes.remove(('inet:server', '1.2.3.4:12346'))
        nodes.remove(('inet:server', '1.2.3.4:12347'))
        nodes.remove(('inet:server', '[::1]:123'))
        nodes.remove(('inet:server', '[1:2:3:4:5:6:7:8]:123'))
        nodes.remove(('inet:email', 'BOB@WOOT.COM'))
        nodes.remove(('inet:email', 'visi@vertex.link'))
        nodes.remove(('it:sec:cwe', 'CWE-1'))
        nodes.remove(('it:sec:cwe', 'CWE-12345678'))
        nodes.remove(('inet:ipv6', 'fff0::1'))
        nodes.remove(('inet:ipv6', '::1'))
        nodes.remove(('inet:ipv6', '::1010'))
        nodes.remove(('inet:ipv6', 'ff::'))
        nodes.remove(('inet:ipv6', '0::1'))
        nodes.remove(('inet:ipv6', '0:0::1'))
        nodes.remove(('inet:ipv6', 'ff:fe:fd::1'))
        nodes.remove(('inet:ipv6', 'ffff:ffe:fd:c::1'))
        nodes.remove(('inet:ipv6', '111::333:222'))
        nodes.remove(('inet:ipv6', '111:222::333'))
        nodes.remove(('inet:ipv6', '1:2:3:4:5:6:7:8'))
        nodes.remove(('inet:ipv6', '1:2:3:4:5:6::7'))
        nodes.remove(('inet:ipv6', '1:2:3:4:5::6'))
        nodes.remove(('inet:ipv6', '1:2:3:4::5'))
        nodes.remove(('inet:ipv6', '1:2:3::4'))
        nodes.remove(('inet:ipv6', '1:2::3'))
        nodes.remove(('inet:ipv6', '1::2'))
        nodes.remove(('inet:ipv6', '1::2:3:4:5:6:7'))
        nodes.remove(('inet:ipv6', '1::2:3:4:5:6'))
        nodes.remove(('inet:ipv6', '1::2:3:4:5'))
        nodes.remove(('inet:ipv6', '1::2:3:4'))
        nodes.remove(('inet:ipv6', '1::2:3'))
        nodes.remove(('inet:ipv6', 'a:2::3:4:5:6:7'))
        nodes.remove(('inet:ipv6', 'a:2::3:4:5:6'))
        nodes.remove(('inet:ipv6', 'a:2::3:4:5'))
        nodes.remove(('inet:ipv6', 'a:2::3:4'))
        nodes.remove(('inet:ipv6', 'a:2::3'))
        nodes.remove(('inet:ipv6', '2001:db8:3333:4444:5555:6666:4.3.2.1'))
        nodes.remove(('inet:ipv6', '::3.4.5.6'))
        nodes.remove(('inet:ipv6', '::ffff:4.3.2.2'))
        nodes.remove(('inet:ipv6', '::FFFF:4.3.2.3'))
        nodes.remove(('inet:ipv6', '::ffff:0000:4.3.2.4'))
        nodes.remove(('inet:ipv6', '::1:2:3:4:4.3.2.5'))
        nodes.remove(('inet:ipv6', '::1:2:3:4.3.2.6'))
        nodes.remove(('inet:ipv6', '::1:2:3:4:5:4.3.2.7'))
        nodes.remove(('inet:ipv6', '::ffff:255.255.255.255'))
        nodes.remove(('inet:ipv6', '::ffff:111.222.33.44'))
        nodes.remove(('inet:ipv6', '1:2::3:4.3.2.8'))
        nodes.remove(('inet:ipv6', '1:2:3:4:5:6:7:9'))
        nodes.remove(('inet:ipv6', '1:2:3:4:5:6:7:a'))
        nodes.remove(('inet:ipv6', '1:2:3:4:5:6:7:b'))
        nodes.remove(('inet:ipv6', '1::a'))
        nodes.remove(('inet:ipv6', '1::a:3'))
        nodes.remove(('inet:ipv6', '1:a::3'))
        nodes.remove(('inet:ipv6', 'a:b:c:d:e::6'))
        self.len(0, nodes)

        nodes = set(s_scrape.scrape(data0, 'inet:email'))
        self.len(2, nodes)
        nodes.remove(('inet:email', 'BOB@WOOT.COM'))
        nodes.remove(('inet:email', 'visi@vertex.link'))
        self.len(0, nodes)

        nodes = list(s_scrape.scrape(data1))
        self.len(16, nodes)
        for _ in range(5):
            nodes.remove(('inet:fqdn', 'foo.bar.org'))

        # URLs should not include any trailing periods or commas.
        nodes.remove(('inet:url', 'tcp://foo.bar.org:4665/'))
        nodes.remove(('inet:url', 'tcp://foo.bar.org:4665/'))
        nodes.remove(('inet:url', 'tcp://foo.bar.org:4665/'))
        nodes.remove(('inet:url', 'tcp://foo.bar.org:4665/'))
        nodes.remove(('inet:url', 'tcp://foo.bar.org:4665/,,..a'))

        nodes.remove(('inet:url', 'tcp://[1:2:3:4:5:6:7:8]:1234/'))
        nodes.remove(('inet:url', 'tcp://[1:2:3::4:5:6]:2345/'))
        nodes.remove(('inet:server', '[1:2:3:4:5:6:7:8]:1234'))
        nodes.remove(('inet:server', '[1:2:3::4:5:6]:2345'))
        nodes.remove(('inet:ipv6', '1:2:3:4:5:6:7:8'))
        nodes.remove(('inet:ipv6', '1:2:3::4:5:6'))

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
                      ('eth', '0x001d3F1ef827552Ae1114027BD3ECF1f086bA0F9')))
        nodes.remove(('crypto:currency:address',
                      ('eth', '0x52908400098527886E0F7030069857D2E4169EE7')))
        nodes.remove(('crypto:currency:address',
                      ('eth', '0x8617E340B3D01FA5F11F306F4090FD50E238070D')))
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
                      ('eth', '0x633b354Cf215dFF4ff3D686aFf363Fa0132877f3')))
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
        self.len(9, nodes)
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
        nodes.remove(('crypto:currency:address',
                      ('ada', 'addr1gx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer5pnz75xxcrzqf96k')))
        nodes.remove(('crypto:currency:address',
                      ('ada', 'addr1yx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzerkr0vd4msrxnuwnccdxlhdjar77j6lg0wypcc9uar5d2shs2z78ve')))

        nodes = list(s_scrape.scrape(linux_paths))
        nodes = [k for k in nodes if k[0] == 'file:path']

        self.len(13, nodes)
        nodes.remove(('file:path', '/bin/ls'))
        nodes.remove(('file:path', '/bin/foo/bar'))
        nodes.remove(('file:path', '/bin/foo'))
        nodes.remove(('file:path', '/bin/foo//'))
        nodes.remove(('file:path', '/bin/foo//bar'))
        nodes.remove(('file:path', '/home/foo/bar/baz.txt'))
        nodes.remove(('file:path', '/tmp/foo/bar'))
        nodes.remove(('file:path', '/var/run/foo/'))
        nodes.remove(('file:path', '/var/run/foo/bar'))
        nodes.remove(('file:path', '/root/.aaa/bbb'))
        nodes.remove(('file:path', '/root/.aaa/ccc'))
        nodes.remove(('file:path', '/root/.aaa/ddd'))
        nodes.remove(('file:path', '/root/.aaa/eee'))

        nodes = list(s_scrape.scrape(windows_paths))
        nodes = [k for k in nodes if k[0] == 'file:path']

        self.len(15, nodes)
        nodes.remove(('file:path', 'c:\\temp'))
        nodes.remove(('file:path', 'c:\\temp.txt'))
        nodes.remove(('file:path', 'c:\\windows\\'))
        nodes.remove(('file:path', 'c:\\windows\\calc.exe'))
        nodes.remove(('file:path', 'c:\\windows\\system32\\'))
        nodes.remove(('file:path', 'c:\\windows\\system32\\drivers\\usb.sys'))
        nodes.remove(('file:path', 'd:\\foo\\bar.txt'))
        nodes.remove(('file:path', 'd:\\foo\\'))
        nodes.remove(('file:path', 'd:\\foo'))
        nodes.remove(('file:path', 'd:\\foo.txt'))
        nodes.remove(('file:path', 'c:\\\\foo\\bar'))
        nodes.remove(('file:path', 'c:\\aaa\\bbb'))
        nodes.remove(('file:path', 'c:\\aaa\\ccc'))
        nodes.remove(('file:path', 'c:\\aaa\\ddd'))
        nodes.remove(('file:path', 'c:\\aaa\\eee'))

        nodes = list(s_scrape.scrape(unc_paths))
        nodes = [k for k in nodes if k[0] == 'inet:url']

        self.len(21, nodes)

        nodes.remove(('inet:url', 'smb://foo/bar/baz'))
        nodes.remove(('inet:url', 'smb://server/share'))
        nodes.remove(('inet:url', 'smb://server.domain.com/share/path/to/filename.txt'))
        nodes.remove(('inet:url', 'smb://1.2.3.4/share'))
        nodes.remove(('inet:url', 'smb://1.2.3.4/share/dirn'))
        nodes.remove(('inet:url', 'smb://1234:2345::345/share'))
        nodes.remove(('inet:url', 'smb://1234:2345::345/share/dirn'))
        nodes.remove(('inet:url', 'smb://1:2:3:4:5:6:7:8/share/filename.txt'))
        nodes.remove(('inet:url', 'smb://server.domain.com/share/path/to/filename1.txt'))
        nodes.remove(('inet:url', 'smb://server.domain.com/share/path/to/filename2.txt'))
        nodes.remove(('inet:url', 'smb://badserver/share/malicious file with spaces.txt'))
        nodes.remove(('inet:url', 'smb://badserver/share/malicious file with spaces.txt'))
        nodes.remove(('inet:url', 'smb://badserver/share/filename'))
        nodes.remove(('inet:url', 'https://server/share/foo.txt'))
        nodes.remove(('inet:url', 'smb://server:1234/share/foo.txt'))
        nodes.remove(('inet:url', 'https://server:1234/share/foo.txt'))
        nodes.remove(('inet:url', 'https://[0::1]:1234/share/foo.txt'))
        AAA = 'A' * 250
        nodes.remove(('inet:url', f'smb://server/share/{AAA}.txt:sname:stype'))
        nodes.remove(('inet:url', 'smb://1:2:3:4:5:6:7:8/share'))
        nodes.remove(('inet:url', 'smb://1:2:3:4:5:6:7:8/share'))

    async def test_scrape_async(self):
        text = 'log4j vuln CVE-2021-44228 is pervasive'
        ndefs = await s_t_utils.alist(s_scrape.scrapeAsync(text))
        self.eq(ndefs, (('it:sec:cve', 'CVE-2021-44228'),))

        regx = regex.compile('(?P<valu>CVE-[0-9]{4}-[0-9]{4,})(?:[^a-z0-9]|$)')
        infos = s_scrape._genMatchList(text, regx, {})
        self.eq(infos, [{'match': 'CVE-2021-44228', 'offset': 11, 'valu': 'CVE-2021-44228'}])

        text = 'endashs are a vulnerability  CVE\u20132022\u20131138 '
        infos = await s_t_utils.alist(s_scrape.contextScrapeAsync(text))
        self.eq(infos, [{'match': 'CVE–2022–1138', 'offset': 29, 'valu': 'CVE-2022-1138', 'form': 'it:sec:cve'}])

        infos = s_scrape._contextScrapeList(text)
        self.eq(infos, [{'match': 'CVE–2022–1138', 'offset': 29, 'valu': 'CVE-2022-1138', 'form': 'it:sec:cve'}])

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

        txt = f'hehe trickbot.bazar haha'
        self.isin('trickbot.bazar', [n[1] for n in s_scrape.scrape(txt)])

    def test_refang(self):
        defanged = '10[.]0[.]0[.]1'
        refanged = '10.0.0.1'
        self.eq({refanged}, {n[1] for n in s_scrape.scrape(defanged)})

        defanged = '10.]0[.0[.]1'
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

        defanged = 'http[://foo.faz.com[:]12312/bam'
        refanged = 'http://foo.faz.com:12312/bam'
        self.eq({refanged, 'foo.faz.com'}, {n[1] for n in s_scrape.scrape(defanged)})

        defanged = 'https[://foo.faz.com[:]12312/bam'
        refanged = 'https://foo.faz.com:12312/bam'
        self.eq({refanged, 'foo.faz.com'}, {n[1] for n in s_scrape.scrape(defanged)})

        defanged = 'hxxp[://foo.faz.com[:]12312/bam'
        refanged = 'http://foo.faz.com:12312/bam'
        self.eq({refanged, 'foo.faz.com'}, {n[1] for n in s_scrape.scrape(defanged)})

        defanged = 'hxxps[://foo.faz.com[:]12312/bam'
        refanged = 'https://foo.faz.com:12312/bam'
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

        defanged = 'https://foo[dot]com/'
        refanged = 'https://foo.com/'
        self.eq({refanged, 'foo.com'}, {n[1] for n in s_scrape.scrape(defanged)})

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

        defanged = '''
        http[:]//test1.com
        https[:]//test2.com
        http[://]test3.com
        https[://]test4.com
        http(:)//test5.com
        https(:)//test6.com
        '''
        exp = {
            'http://test1.com', 'test1.com',
            'https://test2.com', 'test2.com',
            'http://test3.com', 'test3.com',
            'https://test4.com', 'test4.com',
            'http://test5.com', 'test5.com',
            'https://test6.com', 'test6.com',
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

        r = [r for r in results if r.get('valu') == ('eth', '0x52908400098527886E0F7030069857D2E4169EE7')][0]
        self.eq(r, {'form': 'crypto:currency:address',
                    'offset': 430,
                    'match': '0x52908400098527886E0F7030069857D2E4169EE7',
                    'valu': ('eth', '0x52908400098527886E0F7030069857D2E4169EE7')}
                )

        r = [r for r in results if r.get('valu') == 'https://legitcorp.com/blah/giggle.html'][0]
        self.eq(r, {'form': 'inet:url',
                    'match': 'hxxp[s]://legitcorp[.]com/blah/giggle.html',
                    'offset': 575,
                    'valu': 'https://legitcorp.com/blah/giggle.html'})

        # Assert match value matches...
        for r in results:
            erv = r.get('match')
            offs = r.get('offset')
            fv = data3[offs:offs + len(erv)]
            self.eq(erv, fv)

    def test_scrape_cpe(self):

        nodes = sorted(set(s_scrape.scrape(cpedata, ptype='it:sec:cpe')))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:*:*:*:*:*:*:*:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:*:-:na:*:*:*:*:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:*:.:dot:*:*:*:*:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:*:\\!:quoted:*:*:*:*:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:*:\\*:quoted:*:*:*:*:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:*:\\?:quoted:*:*:*:*:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:*:\\\\:escapeescape:*:*:*:*:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:*:_:underscore:*:*:*:*:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:*:langtest:*:*:*:*:*:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:*:langtest:*:*:*:*:-:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:*:langtest:*:*:*:*:en:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:*:langtest:*:*:*:*:usa-123:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:*:langtest:*:*:*:*:usa-en:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:*:langtest:*:*:*:*:usa:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:-:*:*:*:*:*:*:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:a:*:*:*:*:*:*:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:a:apple:swiftnio_http\\/2:1.19.1:*:*:*:*:swift:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:a:daemon-ng:hurray\\:\\::0.x:*:*:*:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:a:foo\\\\bar:big\\$money_2010:*:*:*:*:special:ipod_touch:80gb:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:a:fooo:bar_baz\\:_beep_bpp_sys:1.1:*:*:*:*:ios:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:a:hp:insight:7.4.0.1570:-:*:*:online:win2003:x64:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:a:hp:openview_network_manager:7.51:*:*:*:*:linux:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:a:lemonldap-ng:apache\\:\\:session\\:\\:browsable:0.9:*:*:*:*:perl:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:a:microsoft:intern\\^et_explorer:8.0.6001:beta:*:*:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:a:ntp:ntp:4.2.8:p3:*:*:*:*:*:*'))
        nodes.remove(('it:sec:cpe',
                      'cpe:2.3:a:vendor:product:version:update:edition:lng:sw_edition:target_sw:target_hw:other'))
        nodes.remove(('it:sec:cpe',
                      'cpe:2.3:a:vendor:product:version:update:edition:lng:sw_edition:target_sw:target_hw:tspace'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:h:*:*:*:*:*:*:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:o:*:*:*:*:*:*:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:o:microsoft:windows_7:-:sp2:*:*:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:a:vertex:synapse:*:*:*:*:*:*:*:dquotes'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:a:vertex:synapse:*:*:*:*:*:*:*:MiXeDcAsE'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:a:vertex:synapse:*:*:*:*:*:*:*:squotes'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:a:*:*:*:*:*:*:*:*:*:hasperiod.'))
        nodes.remove(('it:sec:cpe',
                      'cpe:2.3:a:vendor:product:version:update:edition:lng:sw_edition:target_sw:target_hw:otherxxx'))
        nodes.remove(('it:sec:cpe',
                      'cpe:2.3:a:vendor:product:version:update:edition:lng:sw_edition:target_sw:target_hw:otherzzz'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:a:*:*:*:*:*:*:*:*:*:noexclaim'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:a:*:*:*:*:*:*:*:*:*:noslash'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:a:*:*:*:*:*:*:*:*:*:unicodeend0'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:a:*:*:*:*:*:*:*:*:*:smartquotes'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:*:?why??:*:*:*:*:*:*:*:*:*'))
        nodes.remove(('it:sec:cpe', 'cpe:2.3:*:*why*:*:*:*:*:*:*:*:*:*'))

        self.len(0, nodes)

    def test_scrape_uris(self):

        nodes = list(s_scrape.scrape('http://vertex.link https://woot.com'))
        self.len(4, nodes)
        self.isin(('inet:url', 'http://vertex.link'), nodes)
        self.isin(('inet:url', 'https://woot.com'), nodes)
        self.isin(('inet:fqdn', 'vertex.link'), nodes)
        self.isin(('inet:fqdn', 'woot.com'), nodes)

        nodes = list(s_scrape.scrape('ftps://files.vertex.link tcp://1.2.3.4:8080'))
        self.len(5, nodes)
        self.isin(('inet:url', 'ftps://files.vertex.link'), nodes)
        self.isin(('inet:url', 'tcp://1.2.3.4:8080'), nodes)
        self.isin(('inet:fqdn', 'files.vertex.link'), nodes)
        self.isin(('inet:ipv4', '1.2.3.4'), nodes)
        self.isin(('inet:server', '1.2.3.4:8080'), nodes)

        nodes = list(s_scrape.scrape('invalidscheme://vertex.link newp://woot.com'))
        self.len(2, nodes)
        self.isin(('inet:fqdn', 'vertex.link'), nodes)
        self.isin(('inet:fqdn', 'woot.com'), nodes)

        nodes = list(s_scrape.scrape('[https://vertex.link] (http://woot.com)'))
        self.len(4, nodes)
        self.isin(('inet:url', 'https://vertex.link'), nodes)
        self.isin(('inet:url', 'http://woot.com'), nodes)
        self.isin(('inet:fqdn', 'vertex.link'), nodes)
        self.isin(('inet:fqdn', 'woot.com'), nodes)

        nodes = list(s_scrape.scrape('HTTP://vertex.link HTTPS://woot.com'))
        self.len(4, nodes)
        self.isin(('inet:url', 'HTTP://vertex.link'), nodes)
        self.isin(('inet:url', 'HTTPS://woot.com'), nodes)
        self.isin(('inet:fqdn', 'vertex.link'), nodes)
        self.isin(('inet:fqdn', 'woot.com'), nodes)

        nodes = list(s_scrape.scrape('hxxps://vertex[.]link hXXp://woot[.]com'))
        self.len(4, nodes)
        self.isin(('inet:url', 'https://vertex.link'), nodes)
        self.isin(('inet:url', 'http://woot.com'), nodes)
        self.isin(('inet:fqdn', 'vertex.link'), nodes)
        self.isin(('inet:fqdn', 'woot.com'), nodes)

        nodes = list(s_scrape.scrape('hxxp[:]//vertex(.)link hXXps[://]woot[.]com'))
        self.len(4, nodes)
        self.isin(('inet:url', 'http://vertex.link'), nodes)
        self.isin(('inet:url', 'https://woot.com'), nodes)
        self.isin(('inet:fqdn', 'vertex.link'), nodes)
        self.isin(('inet:fqdn', 'woot.com'), nodes)
