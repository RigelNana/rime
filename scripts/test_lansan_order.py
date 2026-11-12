"""字词调整的顺序约束回归；运行 python -m unittest discover -s scripts。"""

import unittest

from merge_lansan_dicts import (
    apply_char_word_order, apply_frequency_order, apply_charset_order,
    apply_candidate_prefixes, is_gb2312_han,
)


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


class CharsetOrderTests(unittest.TestCase):
    def test_rare_characters_no_longer_separate_phrases(self):
        rows = group('admf', ['漏', '𥄪', '漏雨', '泪雨'])
        result, pure, stats = apply_charset_order(rows, {'漏'})
        self.assertEqual(candidates(result, 'admf'), ['漏', '漏雨', '泪雨', '𥄪'])
        self.assertEqual(pure, {})
        self.assertEqual(stats['promoted_phrase_rows'], 2)

    def test_gb2312_shortest_code_is_protected_outside_tgh(self):
        rows = group('shhd', ['摺', '据闻', '接事', '撒手闭眼'])
        result, pure, _ = apply_charset_order(rows, set())
        self.assertEqual(result, rows)
        self.assertEqual(pure, {})

    def test_gb2312_long_code_has_no_protection(self):
        rows = group('ab', ['摺']) + group('abcd', ['摺', '甲词', '乙词'])
        result, _, _ = apply_charset_order(rows, set())
        self.assertEqual(candidates(result, 'abcd'), ['甲词', '乙词', '摺'])

    def test_pure_order_is_recorded_when_characters_cross(self):
        rows = group('abcd', ['㐀', '甲', '甲词'])
        result, pure, stats = apply_charset_order(rows, {'甲'})
        self.assertEqual(candidates(result, 'abcd'), ['甲', '甲词', '㐀'])
        self.assertEqual(pure, {'abcd': '㐀甲'})
        self.assertEqual(stats['pure_order_restored_codes'], 1)

    def test_word_order_and_rare_character_order_are_stable(self):
        rows = group('abcd', ['㐀', '乙词', '㐁', '甲词'])
        result, _, _ = apply_charset_order(rows, set())
        self.assertEqual(candidates(result, 'abcd'), ['乙词', '甲词', '㐀', '㐁'])
        self.assertEqual({tuple(r[:2]) for r in result}, {tuple(r[:2]) for r in rows})

    def test_pure_and_special_codes_are_unchanged(self):
        rows = group('abcd', ['㐀', '甲']) + group('a[', ['㐀', '甲词'])
        result, pure, _ = apply_charset_order(rows, {'甲'})
        self.assertEqual(result, rows)
        self.assertEqual(pure, {})


class CandidatePrefixTests(unittest.TestCase):
    def test_only_first_phrase_is_promoted_and_later_words_keep_order(self):
        rows = group('ronm', ['昫', '电梯口', '最高领奖台', '痀'])
        result, _ = apply_candidate_prefixes(rows, {'ronm': ['电梯口']}, {'昫'})
        self.assertEqual(candidates(result, 'ronm'), ['电梯口', '昫', '最高领奖台', '痀'])

    def test_character_exception_keeps_first_and_moves_word_to_second(self):
        rows = group('hhbm', ['翀', '崌', '戳中', '𫊼'])
        result, _ = apply_candidate_prefixes(rows, {'hhbm': ['翀', '戳中']}, {'翀', '崌'})
        self.assertEqual(candidates(result, 'hhbm'), ['翀', '戳中', '崌', '𫊼'])

    def test_named_character_can_be_promoted_without_reordering_words(self):
        rows = group('iiif', ['多寡', '垚', '封土', '圡'])
        result, stats = apply_candidate_prefixes(rows, {'iiif': ['垚']}, {'垚'})
        self.assertEqual(candidates(result, 'iiif'), ['垚', '多寡', '封土', '圡'])
        self.assertEqual(stats['new_character_first_codes'], 1)

    def test_yong_moves_to_second_without_changing_phrase_order(self):
        rows = group('oivi', ['本来以为', '素以', '栐'])
        result, _ = apply_candidate_prefixes(rows, {'oivi': ['本来以为', '栐']}, {'栐'})
        self.assertEqual(candidates(result, 'oivi'), ['本来以为', '栐', '素以'])

    def test_xuan_second_combines_phrase_override_and_pure_order_restoration(self):
        rows = group('sif', ['揎']) + group('sifu', ['玉面', '挂面', '揎', '瑄'])
        rows, _ = apply_frequency_order(rows, {'玉面': 100, '挂面': 50}, {'sifu': ['挂面', '玉面']})
        rows, pure, _ = apply_charset_order(rows, {'瑄'})
        rows, _ = apply_candidate_prefixes(rows, {'sifu': ['挂面', '瑄']}, {'瑄'})
        self.assertEqual(candidates(rows, 'sifu'), ['挂面', '瑄', '玉面', '揎'])
        self.assertEqual(pure['sifu'], '揎瑄')

    def test_stale_or_duplicate_prefix_fails(self):
        rows = group('atst', ['滧', '海底捞'])
        for prefix in [['不存在'], ['海底捞', '海底捞']]:
            with self.assertRaises(ValueError):
                apply_candidate_prefixes(rows, {'atst': prefix}, {'滧'})

    def test_phrase_and_character_internal_order_cannot_change(self):
        rows = group('abcd', ['㐀', '甲词', '㐁', '乙词'])
        for prefix in [['乙词'], ['㐁']]:
            with self.assertRaisesRegex(ValueError, '内部顺序'):
                apply_candidate_prefixes(rows, {'abcd': prefix}, {'㐀', '㐁'})

    def test_gb2312_top_three_remains_mandatory(self):
        rows = group('abcd', ['甲', '甲词', '乙词', '丙词'])
        with self.assertRaisesRegex(ValueError, '前三选'):
            apply_candidate_prefixes(rows, {'abcd': ['甲词', '乙词', '丙词']}, {'甲'})

    def test_redundant_long_code_cannot_be_promoted(self):
        rows = group('a', ['甲']) + group('abcd', ['甲词', '甲'])
        with self.assertRaisesRegex(ValueError, '后置'):
            apply_candidate_prefixes(rows, {'abcd': ['甲']}, {'甲'})

    def test_nonstandard_non_gb_character_cannot_be_promoted(self):
        rows = group('abcd', ['甲词', '㐀'])
        with self.assertRaisesRegex(ValueError, '后置'):
            apply_candidate_prefixes(rows, {'abcd': ['㐀']}, set())


class FrequencyOrderTests(unittest.TestCase):
    def test_global_frequency_can_cross_character_without_old_pair_constraint(self):
        rows = group('alyw', ['法国人', '欺人', '泅', '河南人', '湖南人'])
        result, _ = apply_frequency_order(rows, {'法国人': 9433, '河南人': 1784,
                                                '湖南人': 1140, '欺人': 373})
        self.assertEqual(candidates(result, 'alyw'), ['法国人', '河南人', '泅', '湖南人', '欺人'])

    def test_second_gb2312_character_also_fits_top_three(self):
        rows = group('ofrm', ['本日', '橹', '那一日', '氇', '栢'])
        result, stats = apply_frequency_order(rows, {'本日': 1, '那一日': 2})
        self.assertEqual(candidates(result, 'ofrm'), ['那一日', '橹', '氇', '本日', '栢'])
        self.assertEqual(stats['gb2312_promoted_rows'], 1)

    def test_long_code_keeps_demotion_even_for_gb2312(self):
        rows = group('a', ['甲']) + group('abcd', ['乙词', '甲词', '甲'])
        result, _ = apply_frequency_order(rows, {'甲词': 2, '乙词': 1})
        self.assertEqual(candidates(result, 'a'), ['甲'])
        self.assertEqual(candidates(result, 'abcd'), ['甲词', '乙词', '甲'])

    def test_equal_frequencies_keep_current_order(self):
        rows = group('abcd', ['甲词', '甲', '乙词', '丙词'])
        result, _ = apply_frequency_order(rows, {'甲词': 10, '乙词': 10, '丙词': 10})
        self.assertEqual(result, rows)

    def test_uncovered_words_keep_current_order(self):
        rows = group('abcd', ['甲词', '甲', '乙词', '丙词'])
        result, _ = apply_frequency_order(rows, {'丙词': 10})
        self.assertEqual(candidates(result, 'abcd'), ['丙词', '甲', '甲词', '乙词'])

    def test_non_gb2312_character_moves_only_to_preserve_character_order(self):
        rows = group('abcd', ['甲词', '乙词', '𠀀', '丙词', '甲'])
        result, _ = apply_frequency_order(rows, {'甲词': 3, '乙词': 2, '丙词': 1})
        self.assertEqual(candidates(result, 'abcd'), ['甲词', '𠀀', '甲', '乙词', '丙词'])
        self.assertFalse(is_gb2312_han('𠀀'))
        self.assertFalse(is_gb2312_han('㵘'))

    def test_pure_character_collision_cannot_silently_break_top_three(self):
        with self.assertRaisesRegex(ValueError, '前三选.*冲突'):
            apply_frequency_order(group('abcd', ['甲', '乙', '丙', '丁']), {})

    def test_incompatible_shortcode_rule_cannot_silently_break_top_three(self):
        rows = group('a', ['甲']) + group('abcd', ['甲词', '乙词', '甲', '乙'])
        with self.assertRaisesRegex(ValueError, '前三选.*冲突'):
            apply_frequency_order(rows, {'甲词': 2, '乙词': 1})


if __name__ == '__main__':
    unittest.main()
