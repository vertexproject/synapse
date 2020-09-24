import synapse.lib.scrape as s_scrape

import synapse.tests.utils as s_t_utils

data0 = '''

visi@vertex.link is an email address

and BOB@WOOT.COM is another

    hehe.taxi

    aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa

    aa:bb:cc:dd:ee:ff

    1.2.3.4

    5.6.7.8:16

'''

class ScrapeTest(s_t_utils.SynTest):

    def test_scrape(self):

        nodes = set(s_scrape.scrape(data0))

        self.len(9, nodes)
        nodes.remove(('hash:md5', 'a' * 32))
        nodes.remove(('inet:ipv4', '1.2.3.4'))
        nodes.remove(('inet:ipv4', '5.6.7.8'))
        nodes.remove(('inet:fqdn', 'WOOT.COM'))
        nodes.remove(('inet:fqdn', 'hehe.taxi'))
        nodes.remove(('inet:fqdn', 'vertex.link'))
        nodes.remove(('inet:server', '5.6.7.8:16'))
        nodes.remove(('inet:email', 'BOB@WOOT.COM'))
        nodes.remove(('inet:email', 'visi@vertex.link'))
        self.len(0, nodes)

        nodes = set(s_scrape.scrape(data0, 'inet:email'))
        self.len(2, nodes)
        nodes.remove(('inet:email', 'BOB@WOOT.COM'))
        nodes.remove(('inet:email', 'visi@vertex.link'))
        self.len(0, nodes)

    def test_scrape_sequential(self):
        md5 = ('a' * 32, 'b' * 32, )
        sha1 = ('c' * 40, 'd' * 40, )
        sha256 = ('e' * 64, 'f' * 64, )
        url = ('http://foobar.com', 'http://cat.net', )
        ipv4 = ('1.2.3.4', '5.6.7.8', )
        server = ('7.7.7.7:123', '8.8.8.8:456', )
        fqdn = ('woot.com', 'baz.io', )
        email = ('me@bar.io', 'you@zee.com', )

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

    def test_refang(self):

        defanged = '10[.]0[.]0[.]1'
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

        # Test scrape without re-fang
        defanged = 'HXXP[:]//example.com?faz=hxxp and im talking about HXXP over here'
        self.eq({'example.com'}, {n[1] for n in s_scrape.scrape(defanged, refang=False)})
