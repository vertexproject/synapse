from synapse.tests.common import *

import synapse.lib.encoding as s_encoding

class EncTest(SynTest):

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
