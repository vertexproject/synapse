import os

import synapse.tools.json2mpk as s_json2mpk

import synapse.tests.utils as s_t_utils

class Json2MpkTest(s_t_utils.SynTest):

    def test_tools_json2mpk(self):

        with self.getTestDir() as ndir:

            outp = self.getTestOutp()

            path = os.path.join(ndir, 'woot.json')
            newp = os.path.join(ndir, 'woot.mpk')
            fake = os.path.join(ndir, 'fake.json')
            html = os.path.join(ndir, 'woot.html')

            self.false(os.path.isfile(path))
            self.false(os.path.isfile(newp))

            with open(path, 'wb') as fd:
                fd.write(b'{"foo":10}\n{"bar":20}\n')

            args = ['--rm', path, fake, html]

            s_json2mpk.main(args, outp=outp)

            with open(newp, 'rb') as fd:
                self.eq(fd.read(), b'\x81\xa3foo\n\x81\xa3bar\x14')

            self.false(os.path.isfile(path))
