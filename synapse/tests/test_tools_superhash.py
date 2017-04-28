from synapse.tests.common import *

import synapse.tools.superhash as s_superhash


class SuperhashTest(SynTest):

    def setUp(self):
        self.expected_data = [
            ('null',
             '',
             {'md5': 'd41d8cd98f00b204e9800998ecf8427e',
              'sha1': 'da39a3ee5e6b4b0d3255bfef95601890afd80709',
              'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
              'sha512': 'cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2'
                        '877eec2f63b931bd47417a81a538327af927da3e',
              'guid': '370c1098a47904ea9caeb9f5f71459ba'}),
            ('lazy',
             'The quick brown fox jumps over the lazy dog\n',
             {'md5': '37c4b87edffc5d198ff5a185cee7ee09',
              'sha1': 'be417768b5c3c5c1d9bcb2e7c119196dd76b5570',
              'sha256': 'c03905fcdab297513a620ec81ed46ca44ddb62d41cbbd83eb4a5a3592be26a69',
              'sha512': 'a12ac6bdd854ac30c5cc5b576e1ee2c060c0d8c2bec8797423d7119aa2b962f7f30ce2e39879cbff0109c8f0'
                        'a3fd9389a369daae45df7d7b286d7d98272dc5b1',
              'guid': '7559ce6a45ff7b401be5c9a73bd37464'}),
            ('lazy_cat',
             'The quick brown fox jumps over the lazy cat\n',
             {'md5': 'd0ac96c75453111d844e8360b651f02f',
              'sha1': '7eef8b3ebdc6ec74e46d57d05efb12e3ed64dd31',
              'sha256': '57c8c4b16adf423de873449adfeb2c89dfeec034ba38ef592ee49744cd54a439',
              'sha512': '822cdb4206f91a02a06e1f52e61c8aa4d9ea7ee362b9d6c171df33730f4121cdf652916658c1fcdd0a8ad5e2'
                        '38fc831717c61763971f79e5460397bd9d621187',
              'guid': 'b595576f53532e5e4d9fab50489f4af1'}),
        ]

    def test_plain(self):
        with self.getTestDir() as fdir:
            for fn, s, edict in self.expected_data:
                fp = os.path.join(fdir, fn)
                with open(fp, 'wb') as f:
                    f.write(s.encode())

                outp = self.getTestOutp()
                args = ['-i', fp]
                s_superhash.main(argv=args, outp=outp)
                outp.expect(fp)
                for k, v in edict.items():
                    outp.expect(k)
                    outp.expect(v)

    def check_json_blob(self, obj, fn, edict):
        self.eq(len(obj), 2)
        self.assertIsInstance(obj, list)
        rd = obj[1]
        self.assertIsInstance(rd, dict)
        self.true('props' in rd)
        rd = rd.get('props')
        self.assertIsInstance(rd, dict)
        self.eq(obj[0], edict.get('guid'))
        self.eq(rd.get('name'), fn)
        for htype in ['md5', 'sha1', 'sha256', 'sha512']:
            e = edict.get(htype)
            self.eq(rd.get(htype), e)

    def test_ingest_multiple_files(self):
        with self.getTestDir() as fdir:
            args = ['--ingest', ]
            test_data = []
            for fn, s, edict in self.expected_data:
                fp = os.path.join(fdir, fn)
                with open(fp, 'wb') as f:
                    f.write(s.encode())
                args.append('-i')
                args.append(fp)
                test_data.append((fn, edict))
            # Ordered behavior is expected
            outp = self.getTestOutp()
            s_superhash.main(argv=args, outp=outp)
            r = outp.mesgs[0]
            obj = json.loads(r)
            self.assertIsInstance(obj, list)
            self.eq(len(obj), 3)
            for blob, (fn, edict) in zip(obj, test_data):
                self.check_json_blob(obj=blob, fn=fn, edict=edict)

    def test_ingest(self):
        with self.getTestDir() as fdir:
            for fn, s, edict in self.expected_data:
                fp = os.path.join(fdir, fn)
                with open(fp, 'wb') as f:
                    f.write(s.encode())

                outp = self.getTestOutp()
                args = ['-i', fp, '--ingest']
                s_superhash.main(argv=args, outp=outp)

                r = outp.mesgs[0]
                obj = json.loads(r)
                self.check_json_blob(obj=obj, fn=fn, edict=edict)

    def test_bad_file(self):
        outp = self.getTestOutp()
        s_superhash.main(argv=['-i', 'foobarbaz'], outp=outp)
        outp.expect('Failed to compute superhash for foobarbaz')
