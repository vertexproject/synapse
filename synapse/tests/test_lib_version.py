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

        # version is the canonical string
        self.isinstance(s_version.version, str)

        self.isinstance(s_version.commit, str)
        self.true((s_version.commit == '') or (len(s_version.commit) == 40))

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

    def test_version_pack_core(self):
        # round-trip
        for major, minor, patch, rank in ((0, 0, 0, s_version.RANK_RELEASE),
                                          (1, 2, 3, s_version.RANK_ALPHA),
                                          (s_version.mask20, s_version.mask20, s_version.mask20, s_version.RANK_POST)):
            packed = s_version.packVersionCore(major, minor, patch, rank)
            self.eq(s_version.unpackVersionCore(packed), (major, minor, patch, rank))

        # fits an unsigned 64 bit int
        self.le(s_version.packVersionCore(s_version.mask20, s_version.mask20, s_version.mask20, s_version.RANK_POST), 2 ** 64 - 1)

        # default rank is RANK_RELEASE
        self.eq(s_version.packVersionCore(1, 2, 3), s_version.packVersionCore(1, 2, 3, s_version.RANK_RELEASE))

        # ordering: a final release sorts above its pre-releases; major.minor.patch dominate rank
        dev = s_version.packVersionCore(1, 0, 0, s_version.RANK_DEV)
        prenum = s_version.packVersionCore(1, 0, 0, s_version.RANK_PRE_NUMERIC)
        alpha = s_version.packVersionCore(1, 0, 0, s_version.RANK_ALPHA)
        beta = s_version.packVersionCore(1, 0, 0, s_version.RANK_BETA)
        rc = s_version.packVersionCore(1, 0, 0, s_version.RANK_RC)
        preother = s_version.packVersionCore(1, 0, 0, s_version.RANK_PRE_OTHER)
        rel = s_version.packVersionCore(1, 0, 0, s_version.RANK_RELEASE)
        post = s_version.packVersionCore(1, 0, 0, s_version.RANK_POST)
        self.true(dev < prenum < alpha < beta < rc < preother < rel < post)
        self.true(post < s_version.packVersionCore(1, 0, 1, s_version.RANK_DEV))

    def test_version_pack_full(self):
        # epoch prepended above the core int, fits an unsigned 128 bit int
        low = s_version.packVersionFull(0, 9, 9, 9, s_version.RANK_POST)
        high = s_version.packVersionFull(1, 0, 0, 0, s_version.RANK_DEV)
        self.true(high > low)
        self.le(s_version.packVersionFull(s_version.mask32, s_version.mask20, s_version.mask20, s_version.mask20, s_version.RANK_POST), 2 ** 128 - 1)
        # the low 64 bits are exactly the core int
        self.eq(s_version.packVersionFull(0, 1, 2, 3, s_version.RANK_RC), s_version.packVersionCore(1, 2, 3, s_version.RANK_RC))

    def test_version_semver_rank(self):
        self.eq(s_version.semverRank(None), s_version.RANK_RELEASE)
        self.eq(s_version.semverRank('a20260617'), s_version.RANK_ALPHA)
        self.eq(s_version.semverRank('alpha.1'), s_version.RANK_ALPHA)
        self.eq(s_version.semverRank('b2'), s_version.RANK_BETA)
        self.eq(s_version.semverRank('beta'), s_version.RANK_BETA)
        self.eq(s_version.semverRank('rc1'), s_version.RANK_RC)
        self.eq(s_version.semverRank('RC0'), s_version.RANK_RC)
        # a non-numeric unrecognized identifier is still a pre-release, but ranks
        # above rc (closer to release) rather than colliding with alpha
        self.eq(s_version.semverRank('B5CD5743F'), s_version.RANK_PRE_OTHER)
        self.true(s_version.RANK_RC < s_version.RANK_PRE_OTHER < s_version.RANK_RELEASE)
        # an unrecognized tag no longer collides with (and sorts below) a
        # recognized earlier-tier tag
        self.true(s_version.semverRank('z') > s_version.semverRank('b'))
        # a purely-numeric pre-release identifier sorts below alpha (SemVer:
        # numeric identifiers rank below alphanumeric ones)
        self.eq(s_version.semverRank('0.3.7'), s_version.RANK_PRE_NUMERIC)
        self.eq(s_version.semverRank('0.3.rc1'), s_version.RANK_PRE_NUMERIC)
        self.true(s_version.RANK_DEV < s_version.RANK_PRE_NUMERIC < s_version.RANK_ALPHA)
        # regression guard: a numeric pre-release must not outrank a named tier
        self.true(s_version.semverRank('0.3.7') < s_version.semverRank('beta'))

    def test_version_pep440_rank(self):
        import packaging.version as p_version
        self.eq(s_version.pep440Rank(p_version.Version('1.0.0')), s_version.RANK_RELEASE)
        self.eq(s_version.pep440Rank(p_version.Version('1.0.0.dev1')), s_version.RANK_DEV)
        self.eq(s_version.pep440Rank(p_version.Version('1.0.0a1')), s_version.RANK_ALPHA)
        self.eq(s_version.pep440Rank(p_version.Version('1.0.0b2')), s_version.RANK_BETA)
        self.eq(s_version.pep440Rank(p_version.Version('1.0.0rc1')), s_version.RANK_RC)
        self.eq(s_version.pep440Rank(p_version.Version('1.0.0.post1')), s_version.RANK_POST)
        # a pre-release with a dev segment still ranks at the pre-release tier
        self.eq(s_version.pep440Rank(p_version.Version('1.0.0a1.dev1')), s_version.RANK_ALPHA)

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

    def test_version_parseSemver_pep440(self):
        # PEP 440 pre-release suffixes accepted directly (no hyphen)
        data = (
            ('3.0.0a20260617', {'major': 3, 'minor': 0, 'patch': 0, 'pre': 'a20260617'}),
            ('3.0.0b2', {'major': 3, 'minor': 0, 'patch': 0, 'pre': 'b2'}),
            ('3.0.0rc1', {'major': 3, 'minor': 0, 'patch': 0, 'pre': 'rc1'}),
            # Plain release still works
            ('3.0.0', {'major': 3, 'minor': 0, 'patch': 0}),
            # Hyphen pre-release still works
            ('3.0.0-rc1', {'major': 3, 'minor': 0, 'patch': 0, 'pre': 'rc1'}),
        )
        for s, e in data:
            r = s_version.parseSemver(s)
            self.eq(r, e)

    def test_version_verstr_epoch(self):
        # verstr (package versions) accepts an optional PEP 440 epoch prefix; semverstr does not.
        for good in ('1.2.3', '8.0.0', '3.0.0b3', '3!1.2.3', '3!8.0.0', '3!3.0.0b3', '0!1.0.0'):
            self.nn(s_version.ver_re.match(good))

        for bad in ('3!1.2', '3!x', '1.2.3!', '!1.2.3'):
            self.none(s_version.ver_re.match(bad))

        # semverstr (it:semver, EOL/version parsing) rejects the epoch but keeps the plain forms
        # and the PEP 440 a|b|rc pre-release suffix.
        self.nn(s_version.semver_re.match('3.0.0b3'))
        self.none(s_version.semver_re.match('3!8.0.0'))

        # parseSemver uses semverstr, so an epoch string does not parse; plain forms are unchanged.
        self.none(s_version.parseSemver('3!8.0.0'))
        self.eq(s_version.parseSemver('3.0.0b3'), {'major': 3, 'minor': 0, 'patch': 0, 'pre': 'b3'})

    def test_version_verstr_semverstr_aligned(self):
        # verstr is derived from semverstr (semverstr + an optional epoch prefix), so they share the
        # exact core grammar and differ ONLY on the epoch. Guard against a future rewrite drifting them.
        self.true(s_version.verstr.endswith(s_version.semverstr[1:]))

        # they agree on every non-epoch string (accept and reject alike)
        for s in ('1.2.3', '8.0.0', '3.0.0b4', '1.2.3-rc.1', '1.2.3+build', '01.2.3', '1.2', 'x', ''):
            self.eq(bool(s_version.ver_re.match(s)), bool(s_version.semver_re.match(s)))

        # the only difference is the epoch: verstr accepts it, semverstr rejects it
        for s in ('3!3.0.0b4', '0!1.2.3'):
            self.nn(s_version.ver_re.match(s))
            self.none(s_version.semver_re.match(s))

    def test_version_release(self):
        # release() with no arg returns the module-level release triple
        self.eq(s_version.release(), s_version.release(s_version.version))

        # PEP 440 pre-release string strips to (3, 0, 0)
        self.eq(s_version.release('3.0.0a20260617'), (3, 0, 0))

        # Plain string
        self.eq(s_version.release('3.0.0'), (3, 0, 0))

        # Legacy tuple passthrough
        self.eq(s_version.release((3, 0, 0)), (3, 0, 0))

        # Short tuple is padded to 3 elements
        self.eq(s_version.release((2, 1)), (2, 1, 0))

    def test_version_parse(self):
        # parse() returns a packaging.version.Version
        self.eq(s_version.parse((3, 0, 0)), s_version.parse('3.0.0'))

        # Pre-release sorts below the release
        self.lt(s_version.parse('3.0.0a1'), s_version.parse('3.0.0'))

    def test_version_req_string(self):
        # reqVersion now accepts a version string
        self.none(s_version.reqVersion('3.0.0', '>=3.0.0'))

        # Legacy tuple still accepted
        self.none(s_version.reqVersion((3, 0, 0), '>=3.0.0'))

        # Pre-release is below 3.0.0 — should raise
        with self.raises(s_exc.BadVersion):
            s_version.reqVersion('3.0.0a1', '>=3.0.0')

    def test_version_matches_extended(self):
        # PEP 440 pre-release is less than its release
        self.false(s_version.matches('3.0.0a20260617', '>=3.0.0'))

        # Legacy tuple still works
        self.true(s_version.matches((3, 0, 0), '>=3.0.0'))

    def test_version_canonical_derived(self):
        # version is the canonical string
        self.isinstance(s_version.version, str)
