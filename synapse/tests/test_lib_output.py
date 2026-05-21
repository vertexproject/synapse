import synapse.tests.utils as s_t_utils

import synapse.lib.output as s_output

class TestOutPut(s_t_utils.SynTest):

    # def test_output(self):
    #     outp = s_output.OutPut()
    #     outp.printf('foo')
    #     outp.printf('bar')

    def test_output_bytes(self):
        outp = s_output.OutPutBytes()

        outp.printf('foo')
        outp.printf('bar')

        outp.fd.seek(0)
        self.eq(outp.fd.read(), b'foo\nbar\n')

    def test_output_str(self):
        outp = s_output.OutPutStr()
        outp.printf('foo')
        outp.printf('bar')

        self.eq(str(outp), 'foo\nbar\n')
