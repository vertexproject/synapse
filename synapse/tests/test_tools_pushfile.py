import os
import hashlib

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.scope as s_scope
import synapse.tools.pushfile as s_pushfile

import synapse.tests.utils as s_t_utils

nullhash = hashlib.sha256(b'').digest()
visihash = hashlib.sha256(b'visi').digest()

class TestPushFile(s_t_utils.SynTest):
    def test_pushfile(self):
        with s_coro.AsyncToSyncCMgr(self.getTestDmonCortexAxon) as dmon:
            coreurl = s_scope.get('coreurl')
            axonurl = s_scope.get('axonurl')
            dirn = s_scope.get('dirn')

            nullpath = os.path.join(dirn, 'null.txt')
            visipath = os.path.join(dirn, 'visi.txt')

            with s_common.genfile(visipath) as fd:
                fd.write(b'visi')

            with self.getTestProxy(dmon, 'axon00') as axon:
                self.len(1, axon.wants([visihash]))

            outp = self.getTestOutp()
            args = ['-a', axonurl,
                    '-c', coreurl,
                    '-t', 'foo.bar,baz.faz',
                    visipath]
            self.eq(0, s_pushfile.main(args, outp))
            self.true(outp.expect('Uploaded [visi.txt] to axon'))
            self.true(outp.expect('file: visi.txt (4) added to core'))

            with self.getTestProxy(dmon, 'axon00') as axon:
                self.len(0, axon.wants([visihash]))
                self.eq(b'visi', b''.join([buf for buf in axon.get(visihash)]))
            outp = self.getTestOutp()
            self.eq(0, s_pushfile.main(args, outp))
            self.true(outp.expect('Axon already had [visi.txt]'))

            with self.getTestProxy(dmon, 'core', user='root', passwd='root') as core:
                self.len(1, core.eval(f'file:bytes={s_common.ehex(visihash)}'))
                self.len(1, core.eval('file:bytes:size=4'))
                self.len(1, core.eval('#foo.bar'))
                self.len(1, core.eval('#baz.faz'))

            # Ensure user can't push a non-existant file and that it won't exist
            args = ['-a', axonurl, nullpath]
            self.raises(s_exc.NoSuchFile, s_pushfile.main, args, outp=outp)

            with self.getTestProxy(dmon, 'axon00') as axon:
                self.len(1, axon.wants([nullhash]))

            with s_common.genfile(nullpath) as fd:
                fd.write(b'')

            outp = self.getTestOutp()
            args = ['-a', axonurl,
                    '-c', coreurl,
                    '-t', 'empty',
                    nullpath]
            self.eq(0, s_pushfile.main(args, outp))

            with self.getTestProxy(dmon, 'axon00') as axon:
                self.len(0, axon.wants([nullhash]))
                self.eq(b'', b''.join([buf for buf in axon.get(nullhash)]))
