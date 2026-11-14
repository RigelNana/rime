import unittest

from build_lansan_decomposition import derive_code, render_table


class DecompositionTests(unittest.TestCase):
    def test_compact_roots_and_actual_full_code(self):
        row = dict(text='没', code='ahbx', roots='氵 几 又', root_ids='氵 几 又', suffix='x')
        keys = {'氵': 'a', '几': 'h', '又': 'b'}
        self.assertEqual(render_table([row], {'没': {'a', 'ahb', 'ahbx'}}, keys),
                         '没\t〔氵几又&nbsp;·&nbsp;ahbx〕\n')

    def test_four_or_more_roots_take_first_three_and_last(self):
        row = dict(text='某', root_ids='甲 乙 丙 丁 戊', suffix='')
        self.assertEqual(derive_code(row, dict(zip('甲乙丙丁戊', 'abcde'))), 'abce')

    def test_single_root_and_explicit_yi_exception(self):
        self.assertEqual(derive_code(dict(text='木', root_ids='木', suffix='fi'), {'木': 'o'}), 'ofi')
        self.assertEqual(derive_code(dict(text='一', root_ids='1', suffix='ff'), {'1': 'f'}), 'fjj')

    def test_mismatch_is_rejected_instead_of_displaying_wrong_split(self):
        row = dict(text='𪜶', code='klcd', roots='亻 囗 大', root_ids='亻 囗 大', suffix='d')
        keys = {'亻': 'k', '囗': 'l', '大': 'c'}
        with self.assertRaisesRegex(ValueError, '不匹配'):
            render_table([row], {'𪜶': {'kgcd'}}, keys)
        row['code'] = 'kgcd'
        with self.assertRaisesRegex(ValueError, '不符'):
            render_table([row], {'𪜶': {'kgcd'}}, keys)

    def test_duplicate_cannot_create_an_extra_candidate(self):
        row = dict(text='木', code='ofi', roots='木', root_ids='木', suffix='fi')
        with self.assertRaisesRegex(ValueError, '重复'):
            render_table([row, row], {'木': {'ofi'}}, {'木': 'o'})


if __name__ == '__main__':
    unittest.main()
