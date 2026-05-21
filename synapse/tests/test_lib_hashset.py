import io
import binascii

import synapse.tests.utils as s_t_utils

import synapse.lib.hashset as s_hashset

asdf = b'asdfasdf'
asdfhash = '6a204bd89f3c8348afd5c77c717a097a'
asdfhash_iden = '1c753abfe85b4cbe46584fa5b1834fa4'
asdfhashb = binascii.unhexlify(asdfhash)

class HashsetTest(s_t_utils.SynTest):
    def hashset_assertions(self, hset):
        '''
        Test assertions for the hashset

        Args:
            hset (s_hashset.HashSet):
        '''
        self.eq(hset.size, 8)

        guid, props = hset.guid()
        self.eq(guid, asdfhash_iden)
        self.isinstance(props, dict)
        self.eq(props.get('md5'), asdfhash)
        self.isin('sha1', props)
        self.isin('sha256', props)
        self.isin('sha512', props)
        self.eq(props.get('size'), 8)

        digests = hset.digests()
        self.len(4, digests)
        hdict = dict(digests)
        self.eq(hdict.get('md5'), asdfhashb)
        self.isin('sha1', hdict)
        self.isin('sha256', hdict)
        self.isin('sha512', hdict)

    def test_lib_hashset_base(self):
        hset = s_hashset.HashSet()
        hset.update(asdf)
        self.hashset_assertions(hset)

    def test_lib_hashset_eatfd(self):
        fd = io.BytesIO(asdf)
        hset = s_hashset.HashSet()
        hset.eatfd(fd)
        self.hashset_assertions(hset)
