import io
import json

import synapse.common as s_common

import synapse.lib.msgpack as s_msgpack
import synapse.lib.encoding as s_encoding

import synapse.tests.utils as s_t_utils

testxml = b'''<?xml version="1.0"?>
<data>

    <dnsa fqdn="foo.com" ipv4="1.2.3.4"/>
    <dnsa fqdn="bar.com" ipv4="5.6.7.8"/>

    <urls>
        <badurl>http://evil.com/</badurl>
        <badurl>http://badguy.com/</badurl>
    </urls>

</data>
'''

testlines = b'''
foo.com
bar.com
'''

class EncTest(s_t_utils.SynTest):

    def test_lib_encoding_en(self):
        self.eq(s_encoding.encode('base64', b'visi'), b'dmlzaQ==')
        self.eq(s_encoding.encode('utf8,base64', 'visi'), b'dmlzaQ==')
        self.eq(s_encoding.encode('utf8,base64,-utf8', 'visi'), 'dmlzaQ==')

    def test_lib_encoding_de(self):
        self.eq(s_encoding.decode('base64', b'dmlzaQ=='), b'visi')
        self.eq(s_encoding.decode('base64,utf8', b'dmlzaQ=='), 'visi')
        self.eq(s_encoding.decode('+utf8,base64,utf8', 'dmlzaQ=='), 'visi')

        self.eq(s_encoding.decode('base64', 'dmlzaQ=='), 'visi')
        self.eq(s_encoding.decode('base64', b'dmlzaQ=='), b'visi')

    def test_fmt_csv(self):
        with self.getTestDir() as dirn:
            csvp = s_common.genpath(dirn, 'woot.csv')

            with s_common.genfile(csvp) as fd:
                fd.write(b'#THIS IS A COMMENT\n')
                fd.write(b'foo.com,1.2.3.4\n')
                fd.write(b'vertex.link,5.6.7.8\n')

            fd = s_common.genfile(csvp)

            genr = s_encoding.iterdata(fd, format='csv')
            lines = list(genr)
            self.len(3, lines)
            self.eq(lines[0], ['#THIS IS A COMMENT'])
            self.eq(lines[1], ['foo.com', '1.2.3.4'])
            self.eq(lines[2], ['vertex.link', '5.6.7.8'])
            self.true(fd.closed)

            # keep fd open if we want it left open
            with s_common.genfile(csvp) as fd:
                lines = list(s_encoding.iterdata(fd, close_fd=False,
                                                 format='csv'))
                self.false(fd.closed)

    def test_fmt_json(self):

        testjson = b'''{
            "fqdn": "spooky.com",
            "ipv4": "192.168.1.1",
            "aliases": ["foo", "bar", "baz"]
        }'''
        with self.getTestDir() as dirn:
            jsonp = s_common.genpath(dirn, 'woot.json')
            with s_common.genfile(jsonp) as fd:
                fd.write(testjson)

            with s_common.genfile(jsonp) as fd:
                lines = list(s_encoding.iterdata(fd, close_fd=False,
                                                 format='json'))

                e = [{'fqdn': 'spooky.com',
                      'ipv4': '192.168.1.1',
                      'aliases': ['foo', 'bar', 'baz']}]
                self.eq(lines, e)

    def test_fmt_jsonl(self):
        testjsonl = b'''{"fqdn": "spooky.com", "ipv4": "192.168.1.1"}
{"fqdn":"spookier.com", "ipv4":"192.168.1.2"}'''
        with self.getTestDir() as dirn:
            jsonlp = s_common.genpath(dirn, 'woot.jsonl')
            with s_common.genfile(jsonlp) as fd:
                fd.write(testjsonl)

            with s_common.genfile(jsonlp) as fd:
                lines = list(s_encoding.iterdata(fd, close_fd=False,
                                                 format='jsonl'))
                self.len(2, lines)
                e = [
                    {'ipv4': '192.168.1.1', 'fqdn': 'spooky.com'},
                    {'ipv4': '192.168.1.2', 'fqdn': 'spookier.com'},
                ]
                self.eq(lines, e)

    def test_fmt_xml(self):
        with self.getTestDir() as dirn:
            xmlp = s_common.genpath(dirn, 'woot.xml')
            with s_common.genfile(xmlp) as fd:
                fd.write(testxml)

            with s_common.genfile(xmlp) as fd:
                lines = list(s_encoding.iterdata(fd, close_fd=False,
                                                 format='xml'))
                self.len(1, lines)
                line = lines[0]
                elem = line.get('data')
                self.len(3, list(elem))

    def test_fmt_lines(self):
        with self.getTestDir() as dirn:
            linep = s_common.genpath(dirn, 'woot.txt')
            with s_common.genfile(linep) as fd:
                fd.write(testlines)

            with s_common.genfile(linep) as fd:
                lines = list(s_encoding.iterdata(fd, close_fd=False,
                                                 format='lines'))
                self.len(2, lines)
                e = ['foo.com', 'bar.com']
                self.eq(lines, e)

    def test_fmt_mpk(self):
        with self.getTestDir() as dirn:
            fp = s_common.genpath(dirn, 'woot.mpk')
            with s_common.genfile(fp) as fd:
                fd.write(s_msgpack.en('foo.com'))
                fd.write(s_msgpack.en('bar.com'))

            with s_common.genfile(fp) as fd:
                lines = list(s_encoding.iterdata(fd, close_fd=False,
                                                 format='mpk'))
                self.len(2, lines)
                e = ['foo.com', 'bar.com']
                self.eq(lines, e)

    def test_fmt_addFormat(self):

        def _fmt_woot_old(fd, info):
            yield 'old.bad'

        def _fmt_woot(fd, info):
            yield 'woot'

        opts = {'mode': 'r', 'encoding': 'utf8'}

        s_encoding.addFormat('woot', _fmt_woot_old, opts)
        self.nn(s_encoding.fmtyielders.get('woot'))
        s_encoding.addFormat('woot', _fmt_woot, opts)  # last write wins

        with self.getTestDir() as dirn:
            wootp = s_common.genpath(dirn, 'woot.woot')
            with s_common.genfile(wootp) as fd:
                fd.write(b'this is irrelevant, we always yield woot :-)')

            with s_common.genfile(wootp) as fd:
                lines = list(s_encoding.iterdata(fd, close_fd=False,
                                                 format='woot'))
                self.len(1, lines)
                self.eq(lines, ['woot'])

    def test_fmt_bufio(self):

        data = {
            'foo': [
                {'fqdn': 'com', 'tld': True},
                {'fqdn': 'woot.com'},
            ],

            'bar': [
                {'fqdn': 'vertex.link', 'tld': 0},
            ],

            'newp': [
                {'fqdn': 'newp.com', 'tld': 0},
            ],

        }

        buf = io.BytesIO(json.dumps(data).encode())

        lines = list(s_encoding.iterdata(buf, format='json'))
        self.len(1, lines)
        self.eq(lines[0], data)
