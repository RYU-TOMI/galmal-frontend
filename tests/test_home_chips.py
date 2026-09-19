# -*- coding: utf-8 -*-
"""홈의 어휘 칩 — `/v1/vocab.json` 에서 만들어지고, 계약과 순서까지 같은가 (CONTRACT §5).

`discover.js` 는 `TAG_TOP`·`WHEN_CHIPS` 를 **서버가 그린 칩에서 읽는다.** 칩이 비거나 모자라면
`TAG_TOP = []` → 모든 태그가 하위로 분류 → **카드 태그가 조용히 틀린다.** 그래서 빌드가
`chip_problems()` 로 막는다. 여기서는 그 검사가 실제로 틀린 칩을 잡는지 본다.

2026-09-19 실측(대조군): 칩 표식을 일부러 지우면 「그 이후」 매칭이 24 → 79 로 바뀌고
카드 태그 글자가 달라졌다. 검사가 없으면 그게 그대로 배포된다.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site"))

import home  # noqa: E402

VOCAB = {
    "tags": {"top": ["해변", "도시", "미식", "자연", "문화", "온천"], "sub": {}},
    "when": {"fixed": ["이번 주말", "다음 주말", "이번 주", "이번 달", "다음 달"], "patterns": []},
}


class ChipTest(unittest.TestCase):

    def test_chips_follow_vocab_in_order(self):
        page = home.filter_dock(VOCAB)
        self.assertEqual(home.chip_problems(page, VOCAB), [])

    def test_new_tag_appears_as_chip(self):
        """어휘가 바뀌면 칩도 바뀐다 — 손 사본이었을 땐 옛 이름으로 남았다."""
        v = {"tags": {"top": VOCAB["tags"]["top"] + ["스키"]}, "when": VOCAB["when"]}
        page = home.filter_dock(v)
        self.assertIn('data-mood="스키"', page)
        self.assertEqual(home.chip_problems(page, v), [])

    def test_order_matters(self):
        """순서가 계약의 뜻이다(tags.top = 필터 칩 순서). 뒤바뀐 칩은 잡는다."""
        page = home.filter_dock(VOCAB)
        rev = {"tags": {"top": list(reversed(VOCAB["tags"]["top"]))}, "when": VOCAB["when"]}
        self.assertTrue(home.chip_problems(page, rev))

    def test_missing_chips_are_caught(self):
        """칩이 안 그려지면(템플릿이 깨지면) JS 가 빈 목록을 읽는다 — 빌드가 막아야 한다."""
        self.assertEqual(len(home.chip_problems("<div></div>", VOCAB)), 2)

    def test_ui_only_date_chips_have_no_marker(self):
        """「아무때」·「그 이후」·「날짜 지정」은 화면 전용이라 data-when 이 없다 —
        JS 가 표식으로만 어휘 칩을 고르므로, 표식이 붙으면 어휘로 잘못 읽힌다."""
        page = home.filter_dock(VOCAB)
        for ui in ('data-date=""', 'data-date="rest"', 'data-date="custom"'):
            line = [l for l in page.splitlines() if ui in l][0]
            self.assertNotIn("data-when", line)
        self.assertEqual(page.count(" data-when"), len(VOCAB["when"]["fixed"]))

    def test_values_are_escaped(self):
        """어휘는 백엔드가 준다 — 따옴표가 섞여도 속성이 깨지지 않는다."""
        v = {"tags": {"top": ['a"b']}, "when": {"fixed": []}}
        page = home.filter_dock(v)
        self.assertIn('data-mood="a&quot;b"', page)
        self.assertEqual(home.chip_problems(page, v), [])


if __name__ == "__main__":
    unittest.main()
