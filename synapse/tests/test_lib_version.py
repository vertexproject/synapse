"""
synapse - test_lib_version.py
Created on 10/6/17.
"""
import synapse.exc as s_exc
import synapse.tests.utils as s_t_utils
import synapse.lib.version as s_version


class VersionTest(s_t_utils.SynTest):

    def _runreqtest(self, valu, reqver, exp):
        if exp is None:
            self.none(s_version.reqVersion(valu, reqver))
        else:
            with self.raises(exp):
                s_version.reqVersion(valu, reqver)

    def test_req_version(self):

        # Test vectors are laid out in the order:
        #   Vers, reqver, result
        tsts = [
            ((0, 1, 98), '>=0.1.99,<=0.1.101', s_exc.BadVersion),
            ((0, 1, 99), '>=0.1.99,<=0.1.101', None),
            ((0, 1, 100), '>=0.1.99,<=0.1.101', None),
            ((0, 1, 101), '>=0.1.99,<=0.1.101', None),
            ((0, 1, 102), '>=0.1.99,<=0.1.101', s_exc.BadVersion),

            ((0, 1, 0), '>=0.1.0,<0.2.0', None),
            ((0, 1, 100), '>=0.1.0,<0.2.0', None),
            ((0, 2, 0), '>=0.1.0,<0.2.0', s_exc.BadVersion),

            ((0, 2, 0), '>=0.2.0,<0.3.0', None),
            ((0, 1, 51), '>=0.2.0,<0.3.0', s_exc.BadVersion),
            ((0, 2, 51), '>=0.2.0,<0.3.0', None),
            ((0, 2, 51), '>=0.2.0,<0.3.0,!=0.2.51', s_exc.BadVersion),

            ((0, 1, 56), '>=0.2.0,<3.0.0', s_exc.BadVersion),
            ((0, 2, 0), '>=0.2.0,<3.0.0', None),
            ((2, 0, 0), '>=0.2.0,<3.0.0', None),
            ((2, 0, 1), '>=2.0.0,<3.0.0', None),
            ((2, 1, 0), '>=0.2.0,<3.0.0', None),
            ((3, 0, 0), '>=2.0.0,<3.0.0', s_exc.BadVersion),

        ]

        for vec in tsts:
            self._runreqtest(*vec)

    def test_version_basics(self):
        self.eq(s_version.mask20.bit_length(), 20)
        self.eq(s_version.mask60.bit_length(), 60)

        self.isinstance(s_version.version, tuple)
        self.len(3, s_version.version)
        for v in s_version.version:
            self.isinstance(v, int)

        self.isinstance(s_version.verstring, str)
        tver = tuple([int(p) for p in s_version.verstring.split('.')])
        self.eq(tver, s_version.version)

    def test_version_pack(self):
        ver = s_version.packVersion(0)
        self.eq(ver, 0)

        ver = s_version.packVersion(1)
        self.eq(ver, 0x000010000000000)

        # Ensure each value makes it to its position
        ver = s_version.packVersion(1, 2, 3)
        self.eq(ver, 0x000010000200003)

        ver = s_version.packVersion(0xdeadb, 0x33f13, 0x37133)
        self.eq(ver, 0xdeadb33f1337133)

        ver = s_version.packVersion(s_version.mask20, s_version.mask20, s_version.mask20)
        self.eq(ver, s_version.mask60)

        # Input values are masked to ensure they are 20 bits max
        # XXX Or do we want this to throw an exception?
        ver = s_version.packVersion(1 << 20, 1 << 20, 1 << 20)
        self.eq(ver, 0)
        ver = s_version.packVersion((1 << 20) + 1, (1 << 20) + 2, (1 << 20) + 3)
        self.eq(ver, 0x000010000200003)

    def test_version_unpack(self):
        tup = s_version.unpackVersion(0)
        self.eq(tup, (0, 0, 0))

        tup = s_version.unpackVersion(0x000010000000000)
        self.eq(tup, (1, 0, 0))

        tup = s_version.unpackVersion(0x000010000200003)
        self.eq(tup, (1, 2, 3))

        tup = s_version.unpackVersion(0xdeadb33f1337133)
        self.eq(tup, (0xdeadb, 0x33f13, 0x37133))

        tup = s_version.unpackVersion(s_version.mask60)
        self.eq(tup, (s_version.mask20, s_version.mask20, s_version.mask20))

        # Ensure we only snag the data from the 96 bits of input
        # XXX Or do we want this to throw an exception?
        tup = s_version.unpackVersion(1 << 60)
        self.eq(tup, (0, 0, 0))
        tup = s_version.unpackVersion(1 << 60 | s_version.mask60)
        self.eq(tup, (s_version.mask20, s_version.mask20, s_version.mask20))

    def test_version_fmt(self):

        s = s_version.fmtVersion(1)
        self.eq(s, '1')

        s = s_version.fmtVersion(1, 2)
        self.eq(s, '1.2')

        s = s_version.fmtVersion(1, 2, 3)
        self.eq(s, '1.2.3')

        s = s_version.fmtVersion(1, 2, 3)
        self.eq(s, '1.2.3')

        s = s_version.fmtVersion(1, 2, 3, 'b5cd5743f')
        self.eq(s, '1.2.3.b5cd5743f')

        s = s_version.fmtVersion(1, 2, 3, 'B5CD5743F')
        self.eq(s, '1.2.3.b5cd5743f')

        s = s_version.fmtVersion(2016, 2, 'sp3', 'RC1')
        self.eq(s, '2016.2.sp3.rc1')

        self.raises(s_exc.BadTypeValu, s_version.fmtVersion)

    def test_version_extract_parts(self):
        data = (
            ('1', {'major': 1}),
            ('1.2.3-B5CD5743F', {'major': 1, 'minor': 2, 'patch': 3}),
            ('2016-03-01', {'major': 2016, 'minor': 3, 'patch': 1}),
            ('1.2.windows-RC1', {'major': 1, 'minor': 2}),
            ('1.3a2.dev12', {'major': 1}),
            ('V1.2.3', {'major': 1, 'minor': 2, 'patch': 3}),
            ('V1.4.0-RC0', {'major': 1, 'minor': 4, 'patch': 0}),
            ('v2.4.0.0-1', {'major': 2, 'minor': 4, 'patch': 0}),
            ('v2.4.1.0-0.3.rc1', {'major': 2, 'minor': 4, 'patch': 1}),
            ('0.18.1', {'major': 0, 'minor': 18, 'patch': 1}),
            ('0.18rc2', {'major': 0}),
            ('2.0A1', {'major': 2}),
            ('1.0.0-alpha', {'major': 1, 'minor': 0, 'patch': 0}),
            ('1.0.0-alpha.1', {'major': 1, 'minor': 0, 'patch': 0}),
            ('1.0.0-0.3.7', {'major': 1, 'minor': 0, 'patch': 0}),
            ('1.0.0-x.7.z.92', {'major': 1, 'minor': 0, 'patch': 0}),
            ('1.0.0-alpha+001', {'major': 1, 'minor': 0, 'patch': 0}),
            ('1.0.0+20130313144700', {'major': 1, 'minor': 0, 'patch': 0}),
            ('1.0.0-beta+exp.sha.5114f85', {'major': 1, 'minor': 0, 'patch': 0}),
            ('OpenSSL_1_0_2l', {'major': 1, 'minor': 0}),
        )

        for s, e in data:
            r = s_version.parseVersionParts(s)
            self.eq(r, e)

    def test_version_parseSemver(self):
        data = (
            ('1.2.3', {'major': 1, 'minor': 2, 'patch': 3, }),
            ('0.0.1', {'major': 0, 'minor': 0, 'patch': 1, }),
            ('1.2.3-alpha', {'major': 1, 'minor': 2, 'patch': 3,
                             'pre': 'alpha', }),
            ('1.2.3-alpha.1', {'major': 1, 'minor': 2, 'patch': 3,
                       'pre': 'alpha.1', }),
            ('1.2.3-0.3.7', {'major': 1, 'minor': 2, 'patch': 3,
                             'pre': '0.3.7', }),
            ('1.2.3-x.7.z.92', {'major': 1, 'minor': 2, 'patch': 3,
                                'pre': 'x.7.z.92', }),
            ('1.2.3-alpha+001', {'major': 1, 'minor': 2, 'patch': 3,
                                 'pre': 'alpha', 'build': '001'}),
            ('1.2.3+20130313144700', {'major': 1, 'minor': 2, 'patch': 3,
                                      'build': '20130313144700'}),
            ('1.2.3-beta+exp.sha.5114f85', {'major': 1, 'minor': 2, 'patch': 3,
                                            'pre': 'beta', 'build': 'exp.sha.5114f85'}),
            # Real world examples
            ('1.2.3-B5CD5743F', {'major': 1, 'minor': 2, 'patch': 3,
                                 'pre': 'B5CD5743F', }),
            ('V1.2.3', {'major': 1, 'minor': 2, 'patch': 3, }),
            ('V1.4.0-RC0', {'major': 1, 'minor': 4, 'patch': 0,
                            'pre': 'RC0', }),
            ('v2.4.1-0.3.rc1', {'major': 2, 'minor': 4, 'patch': 1,
                                  'pre': '0.3.rc1'}),
            ('0.18.1', {'major': 0, 'minor': 18, 'patch': 1, }),
            # Invalid semvers
            ('1', None),
            ('1.2', None),
            ('2.0A1', None),
            ('0.18rc2', None),
            ('0.0.00001', None),
            ('2016-03-01', None),
            ('v2.4.0.0-1', None),
            ('1.3a2.dev12', None),
            ('OpenSSL_1_0_2l', None),
            ('1.2.windows-RC1', None),
            ('v2.4.1.0-0.3.rc1', None),
        )
        for s, e in data:
            r = s_version.parseSemver(s)
            self.eq(r, e)
