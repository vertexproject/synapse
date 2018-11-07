import synapse.tests.utils as s_t_utils

import synapse.lib.const as s_const

class ConstTest(s_t_utils.SynTest):
    def test_const_kilos(self):
        self.eq(s_const.kilobyte, 10 ** 3)
        self.eq(s_const.megabyte, 10 ** 6)
        self.eq(s_const.gigabyte, 10 ** 9)
        self.eq(s_const.terabyte, 10 ** 12)
        self.eq(s_const.petabyte, 10 ** 15)
        self.eq(s_const.exabyte, 10 ** 18)
        self.eq(s_const.zettabyte, 10 ** 21)
        self.eq(s_const.yottabyte, 10 ** 24)

    def test_const_kibis(self):
        self.eq(s_const.kibibyte, 2 ** 10)
        self.eq(s_const.mebibyte, 2 ** 20)
        self.eq(s_const.gibibyte, 2 ** 30)
        self.eq(s_const.tebibyte, 2 ** 40)
        self.eq(s_const.pebibyte, 2 ** 50)
        self.eq(s_const.exbibyte, 2 ** 60)
        self.eq(s_const.zebibyte, 2 ** 70)
        self.eq(s_const.yobibyte, 2 ** 80)
