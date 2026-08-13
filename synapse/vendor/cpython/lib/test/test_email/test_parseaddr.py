# From the python source, tests/test_email/ does not have direct tests for the
# AddressList set operations. They are only exercised indirectly, through the
# getaddresses() and parseaddr() paths which do not use the operators. Since
# there is not a standalone test to vendor, we have written a simple test on
# its own.

import synapse.vendor.cpython.lib.email._parseaddr as v_parseaddr

import synapse.vendor.utils as s_v_utils

class AddressListVendorTest(s_v_utils.VendorTest):

    def test_addresslist_setops(self):

        alice = 'alice@example.org'
        bob = 'bob@example.org'

        one = v_parseaddr.AddressList(alice)
        two = v_parseaddr.AddressList(bob)

        self.assertEqual(len(one), 1)
        self.assertEqual(one[0], ('', alice))

        # union drops duplicates
        both = one + two
        self.assertEqual(len(both), 2)
        self.assertEqual(len(one + one), 1)

        # in-place union
        one += two
        self.assertEqual(len(one), 2)
        one += two
        self.assertEqual(len(one), 2)

        # difference
        self.assertEqual((both - two).addresslist, [('', alice)])
        self.assertEqual(len(both - both), 0)

        # in-place difference
        both -= two
        self.assertEqual(both.addresslist, [('', alice)])

    def test_addresslist_empty(self):

        empty = v_parseaddr.AddressList(None)
        self.assertEqual(len(empty), 0)
        self.assertEqual(empty.addresslist, [])
