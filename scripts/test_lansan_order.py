"""字词调整的顺序约束回归；运行 python -m unittest discover -s scripts。"""

import unittest

from merge_lansan_dicts import apply_char_word_order


def group(code, texts):
    return [[text, code, str(len(texts) - i)] for i, text in enumerate(texts)]


def candidates(rows, code):
    return [r[0] for r in sorted((r for r in rows if r[1] == code), key=lambda r: -int(r[2]))]


class CharWordOrderTests(unittest.TestCase):
    def test_shortcode_need_not_be_first_candidate_or_prefix(self):
        rows = group('xy', ['乙', '甲']) + group('abcd', ['甲', '甲词', '乙词'])
        result, _ = apply_char_word_order(rows, {})
        self.assertEqual(candidates(result, 'xy'), ['乙', '甲'])
        self.assertEqual(candidates(result, 'abcd'), ['甲词', '乙词', '甲'])

    def test_both_internal_orders_survive_shorthand_demotion(self):
        rows = group('a', ['甲']) + group('abcd', ['甲', '甲词', '乙', '乙词'])
        result, _ = apply_char_word_order(rows, {})
        self.assertEqual(candidates(result, 'abcd'), ['甲词', '乙词', '甲', '乙'])

    def test_reviews_keep_current_phrase_order(self):
        rows = group('abcd', ['教练员', '悄', '快递员'])
        result, _ = apply_char_word_order(rows, {'abcd': [('悄', '快递员', 'word')]})
        self.assertEqual(candidates(result, 'abcd'), ['教练员', '快递员', '悄'])

    def test_character_preference_does_not_jump_over_other_words(self):
        rows = group('abcd', ['打成一片', '球市', '珮', '乙'])
        result, _ = apply_char_word_order(rows, {'abcd': [('珮', '球市', 'character')]})
        self.assertEqual(candidates(result, 'abcd'), ['打成一片', '珮', '球市', '乙'])

    def test_shorthand_has_priority_over_review(self):
        rows = group('a', ['甲']) + group('abcd', ['甲', '甲词'])
        result, _ = apply_char_word_order(rows, {'abcd': [('甲', '甲词', 'character')]})
        self.assertEqual(candidates(result, 'abcd'), ['甲词', '甲'])

    def test_unreviewed_and_pure_groups_are_unchanged(self):
        rows = group('abcd', ['甲', '甲词']) + group('bcde', ['乙词', '丙词']) + group('cdef', ['乙', '丙'])
        result, _ = apply_char_word_order(rows, {'abcd': [('甲', '甲词', 'keep')]})
        self.assertEqual(result, rows)

    def test_contradictory_review_is_not_silently_applied(self):
        rows = group('abcd', ['甲', '甲词', '乙', '乙词'])
        with self.assertRaisesRegex(ValueError, '冲突'):
            apply_char_word_order(rows, {'abcd': [('甲', '乙词', 'word'), ('乙', '甲词', 'character')]})

    def test_stale_review_fails(self):
        with self.assertRaisesRegex(ValueError, '不存在'):
            apply_char_word_order(group('abcd', ['甲', '甲词']), {'abcd': [('甲', '不存在', 'word')]})


if __name__ == '__main__':
    unittest.main()
