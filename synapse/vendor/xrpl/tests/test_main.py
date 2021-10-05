import synapse.vendor.utils as s_v_utils

from synapse.vendor.xrpl.tests.test_main_test_cases import test_cases
from synapse.vendor.xrpl.core import addresscodec
from synapse.vendor.xrpl.core.addresscodec.main import MAX_32_BIT_UNSIGNED_INT


class TestMain(s_v_utils.VendorTest):
    def test_classic_address_to_xaddress(self):
        for test_case in test_cases:
            (
                classic_address,
                tag,
                expected_main_xaddress,
                expected_test_xaddress,
            ) = test_case

            # test
            xaddress = addresscodec.classic_address_to_xaddress(
                classic_address, tag, True
            )
            self.assertEqual(xaddress, expected_test_xaddress)

            # main
            xaddress = addresscodec.classic_address_to_xaddress(
                classic_address, tag, False
            )
            self.assertEqual(xaddress, expected_main_xaddress)

    def test_xaddress_to_classic_address(self):
        for test_case in test_cases:
            (
                expected_classic_address,
                expected_tag,
                main_xaddress,
                test_xaddress,
            ) = test_case

            # test
            classic_address, tag, is_test = addresscodec.xaddress_to_classic_address(
                test_xaddress
            )
            self.assertEqual(classic_address, expected_classic_address)
            self.assertEqual(tag, expected_tag)
            self.assertTrue(is_test)

            # main
            classic_address, tag, is_test = addresscodec.xaddress_to_classic_address(
                main_xaddress
            )
            self.assertEqual(classic_address, expected_classic_address)
            self.assertEqual(tag, expected_tag)
            self.assertFalse(is_test)

    def test_classic_address_to_xaddress_invalid_tag(self):
        classic_address = "rGWrZyQqhTp9Xu7G5Pkayo7bXjH4k4QYpf"
        tag = MAX_32_BIT_UNSIGNED_INT + 1

        self.assertRaises(
            addresscodec.XRPLAddressCodecException,
            addresscodec.classic_address_to_xaddress,
            classic_address,
            tag,
            True,
        )

        self.assertRaises(
            addresscodec.XRPLAddressCodecException,
            addresscodec.classic_address_to_xaddress,
            classic_address,
            tag,
            False,
        )

    def test_classic_address_to_xaddress_bad_classic_address(self):
        classic_address = "r"

        self.assertRaises(
            ValueError,
            addresscodec.classic_address_to_xaddress,
            classic_address,
            None,
            True,
        )

        self.assertRaises(
            ValueError,
            addresscodec.classic_address_to_xaddress,
            classic_address,
            None,
            False,
        )

    def test_is_valid_classic_address_secp256k1(self):
        classic_address = "rU6K7V3Po4snVhBBaU29sesqs2qTQJWDw1"

        result = addresscodec.is_valid_classic_address(classic_address)
        self.assertTrue(result)

    def test_is_valid_classic_address_ed25519(self):
        classic_address = "rLUEXYuLiQptky37CqLcm9USQpPiz5rkpD"

        result = addresscodec.is_valid_classic_address(classic_address)
        self.assertTrue(result)

    def test_is_valid_classic_address_invalid(self):
        classic_address = "rU6K7V3Po4snVhBBaU29sesqs2qTQJWDw2"

        result = addresscodec.is_valid_classic_address(classic_address)
        self.assertFalse(result)

    def test_is_valid_classic_address_empty(self):
        classic_address = ""

        result = addresscodec.is_valid_classic_address(classic_address)
        self.assertFalse(result)

    def test_is_valid_xaddress_valid(self):
        xaddress = "X7AcgcsBL6XDcUb289X4mJ8djcdyKaB5hJDWMArnXr61cqZ"

        result = addresscodec.is_valid_xaddress(xaddress)
        self.assertTrue(result)

    def test_is_valid_xaddress_invalid(self):
        xaddress = "XVLhHMPHU98es4dbozjVtdWzVrDjtV18pX8zeUygYrCgrPh"

        result = addresscodec.is_valid_xaddress(xaddress)
        self.assertFalse(result)

    def test_is_valid_xaddress_empty(self):
        xaddress = ""

        result = addresscodec.is_valid_xaddress(xaddress)
        self.assertFalse(result)
