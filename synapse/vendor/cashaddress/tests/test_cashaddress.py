# It has been modified for vendored imports and vendored test harness.
# keypair specific tests have been commented out.
import synapse.vendor.utils as s_v_utils

from synapse.vendor.cashaddress import convert

# It has been modified for vendored imports.

class TestConversion(s_v_utils.VendorTest):
    def test_to_legacy_p2sh(self):
        self.assertEqual(convert.to_legacy_address('3CWFddi6m4ndiGyKqzYvsFYagqDLPVMTzC'),
                         '3CWFddi6m4ndiGyKqzYvsFYagqDLPVMTzC')
        self.assertEqual(convert.to_legacy_address('bitcoincash:ppm2qsznhks23z7629mms6s4cwef74vcwvn0h829pq'),
                         '3CWFddi6m4ndiGyKqzYvsFYagqDLPVMTzC')

    def test_to_legacy_p2pkh(self):
        self.assertEqual(convert.to_legacy_address('155fzsEBHy9Ri2bMQ8uuuR3tv1YzcDywd4'),
                         '155fzsEBHy9Ri2bMQ8uuuR3tv1YzcDywd4')
        self.assertEqual(convert.to_legacy_address('bitcoincash:qqkv9wr69ry2p9l53lxp635va4h86wv435995w8p2h'),
                         '155fzsEBHy9Ri2bMQ8uuuR3tv1YzcDywd4')

    def test_to_cash_p2sh(self):
        self.assertEqual(convert.to_cash_address('3CWFddi6m4ndiGyKqzYvsFYagqDLPVMTzC'),
                         'bitcoincash:ppm2qsznhks23z7629mms6s4cwef74vcwvn0h829pq')
        self.assertEqual(convert.to_cash_address('bitcoincash:ppm2qsznhks23z7629mms6s4cwef74vcwvn0h829pq'),
                         'bitcoincash:ppm2qsznhks23z7629mms6s4cwef74vcwvn0h829pq')

    def test_to_cash_p2pkh(self):
        self.assertEqual(convert.to_cash_address('155fzsEBHy9Ri2bMQ8uuuR3tv1YzcDywd4'),
                         'bitcoincash:qqkv9wr69ry2p9l53lxp635va4h86wv435995w8p2h')
        self.assertEqual(convert.to_cash_address('bitcoincash:qqkv9wr69ry2p9l53lxp635va4h86wv435995w8p2h'),
                         'bitcoincash:qqkv9wr69ry2p9l53lxp635va4h86wv435995w8p2h')

    def test_to_legacy_p2sh_testnet(self):
        self.assertEqual(convert.to_legacy_address('2MwikwR6hoVijCmr1u8UgzFMHFP6rpQyRvP'),
                         '2MwikwR6hoVijCmr1u8UgzFMHFP6rpQyRvP')
        self.assertEqual(convert.to_legacy_address('bchtest:pqc3tyspqwn95retv5k3c5w4fdq0cxvv95u36gfk00'),
                         '2MwikwR6hoVijCmr1u8UgzFMHFP6rpQyRvP')

    def test_to_legacy_p2pkh_testnet(self):
        self.assertEqual(convert.to_legacy_address('mqp7vM7eU7Vu9NPH1V7s7pPg5FFBMo6SWK'),
                         'mqp7vM7eU7Vu9NPH1V7s7pPg5FFBMo6SWK')
        self.assertEqual(convert.to_legacy_address('bchtest:qpc0qh2xc3tfzsljq79w37zx02kwvzm4gydm222qg8'),
                         'mqp7vM7eU7Vu9NPH1V7s7pPg5FFBMo6SWK')

    def test_to_cash_p2sh_testnet(self):
        self.assertEqual(convert.to_cash_address('2MwikwR6hoVijCmr1u8UgzFMHFP6rpQyRvP'),
                         'bchtest:pqc3tyspqwn95retv5k3c5w4fdq0cxvv95u36gfk00')
        self.assertEqual(convert.to_cash_address('bchtest:pqc3tyspqwn95retv5k3c5w4fdq0cxvv95u36gfk00'),
                         'bchtest:pqc3tyspqwn95retv5k3c5w4fdq0cxvv95u36gfk00')

    def test_to_cash_p2pkh_testnet(self):
        self.assertEqual(convert.to_cash_address('mqp7vM7eU7Vu9NPH1V7s7pPg5FFBMo6SWK'),
                         'bchtest:qpc0qh2xc3tfzsljq79w37zx02kwvzm4gydm222qg8')
        self.assertEqual(convert.to_cash_address('bchtest:qpc0qh2xc3tfzsljq79w37zx02kwvzm4gydm222qg8'),
                         'bchtest:qpc0qh2xc3tfzsljq79w37zx02kwvzm4gydm222qg8')

    def test_is_valid(self):
        self.assertTrue(convert.is_valid('bitcoincash:qqkv9wr69ry2p9l53lxp635va4h86wv435995w8p2h'))
        self.assertTrue(convert.is_valid('2MwikwR6hoVijCmr1u8UgzFMHFP6rpQyRvP'))
        self.assertFalse(convert.is_valid('bitcoincash:aqkv9wr69ry2p9l53lxp635va4h86wv435995w8p2h'))
        self.assertFalse(convert.is_valid('bitcoincash:qqqqqqqq9ry2p9l53lxp635va4h86wv435995w8p2h'))
        self.assertFalse(convert.is_valid('22222wR6hoVijCmr1u8UgzFMHFP6rpQyRvP'))
        self.assertFalse(convert.is_valid(False))
        self.assertFalse(convert.is_valid('Hello World!'))
